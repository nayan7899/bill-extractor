import os
import uvicorn
import requests
import json
import io
import time
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pypdf import PdfReader, PdfWriter
from schemas import ExtractRequest, APIResponse, ExtractionData, TokenUsage

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# --- CONFIGURATION ---
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("CRITICAL ERROR: GEMINI_API_KEY is missing from environment!")
else:
    genai.configure(api_key=api_key)

app = FastAPI(title="HackRx Bill Extractor")

def call_gemini_single_page(mime_type, data_chunk):
    """
    Process a SINGLE page to ensure no data is skipped.
    """
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    generation_config = {
        "response_mime_type": "application/json",
        "max_output_tokens": 8192,
        "temperature": 0.1
    }

    prompt = """
    Analyze this SINGLE page of an invoice.
    Extract all line items visible on this page.

    EXTRACT TO JSON:
    {
      "pagewise_line_items": [
        {
          "page_no": "1",
          "page_type": "Bill Detail", 
          "bill_items": [
            {
              "item_name": "Item Name",
              "item_amount": 0.0, 
              "item_rate": 0.0, 
              "item_quantity": 0.0
            }
          ]
        }
      ]
    }

    RULES:
    1. 'page_type' MUST be exactly: "Bill Detail", "Final Bill", "Pharmacy".
    2. If a value is missing, put 0.0.
    3. Do not markdown.
    """

    try:
        response = model.generate_content(
            [{"mime_type": mime_type, "data": data_chunk}, prompt],
            generation_config=generation_config
        )
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text), response.usage_metadata
    except Exception as e:
        print(f"Page processing error: {e}")
        return {"pagewise_line_items": []}, None

def process_document_smart(file_url):
    print(f"Downloading: {file_url}")
    response = requests.get(file_url, timeout=60)
    response.raise_for_status()
    file_bytes = response.content
    
    content_type = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
    is_pdf = file_url.lower().endswith('.pdf') or 'pdf' in content_type

    combined_data = {"pagewise_line_items": []}
    total_input_tokens = 0
    total_output_tokens = 0

    if is_pdf:
        reader = PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        print(f"PDF detected with {total_pages} pages. Switching to Page-by-Page mode.")

        # STRATEGY: 1 Page per call = 100% Accuracy
        for i in range(total_pages):
            chunk_writer = PdfWriter()
            chunk_writer.add_page(reader.pages[i])
            
            chunk_buffer = io.BytesIO()
            chunk_writer.write(chunk_buffer)
            chunk_bytes = chunk_buffer.getvalue()
            
            print(f"Processing Page {i+1}/{total_pages}...")
            
            # Retry logic for stability
            retries = 2
            chunk_result = {}
            usage = None
            
            for attempt in range(retries):
                try:
                    chunk_result, usage = call_gemini_single_page("application/pdf", chunk_bytes)
                    break
                except Exception as e:
                    print(f"Retry {attempt+1} for page {i+1}...")
                    time.sleep(2)
            
            # FORCE CORRECT PAGE NUMBER
            # We don't trust the AI to know it's on page 5. We tell it.
            if "pagewise_line_items" in chunk_result:
                for page in chunk_result["pagewise_line_items"]:
                    page["page_no"] = str(i + 1)
                    combined_data["pagewise_line_items"].append(page)
            
            if usage:
                total_input_tokens += usage.prompt_token_count
                total_output_tokens += usage.candidates_token_count
            
            # Rate Limit Protection (Gemini Free Tier)
            time.sleep(1)

    else:
        print("Image detected. Sending single request.")
        chunk_result, usage = call_gemini_single_page("image/jpeg", file_bytes)
        combined_data = chunk_result
        if usage:
            total_input_tokens = usage.prompt_token_count
            total_output_tokens = usage.candidates_token_count

    # --- FINAL DATA CLEANUP ---
    if "pagewise_line_items" in combined_data:
        for page in combined_data["pagewise_line_items"]:
            # Fix Types
            raw_type = page.get("page_type", "Bill Detail")
            if "Pharmacy" in raw_type: page["page_type"] = "Pharmacy"
            elif "Final Bill" in raw_type: page["page_type"] = "Final Bill"
            else: page["page_type"] = "Bill Detail"

            # Fill Missing Numbers with 0.0
            if "bill_items" in page and isinstance(page["bill_items"], list):
                valid_items = []
                for item in page["bill_items"]:
                    if not isinstance(item, dict): continue
                    
                    if "item_name" not in item: item["item_name"] = "Unknown Item"

                    for key in ["item_amount", "item_rate", "item_quantity"]:
                        if key not in item:
                            item[key] = 0.0
                        else:
                            try: item[key] = float(item[key])
                            except: item[key] = 0.0
                    
                    valid_items.append(item)
                page["bill_items"] = valid_items
            else:
                page["bill_items"] = []

    tokens = TokenUsage(
        total_tokens=total_input_tokens + total_output_tokens,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens
    )
    
    return combined_data, tokens

@app.post("/extract-bill-data", response_model=APIResponse)
async def extract_bill_data(request: ExtractRequest):
    try:
        raw_data, token_usage = process_document_smart(request.document)
        
        total_count = 0
        if "pagewise_line_items" in raw_data:
            for page in raw_data["pagewise_line_items"]:
                total_count += len(page.get("bill_items", []))

        extraction_data = ExtractionData(
            pagewise_line_items=raw_data.get("pagewise_line_items", []),
            total_item_count=total_count
        )

        return APIResponse(
            is_success=True,
            token_usage=token_usage,
            data=extraction_data
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"is_success": False, "message": f"Processing failed: {str(e)}"}
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
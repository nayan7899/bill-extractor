# 🧾 AI Bill Extractor API (HackRx Submission)

This project is a high-accuracy Document Extraction API built for the HackRx Datathon. It leverages **Google Gemini 2.0 Flash** with a custom **Pagination & Schema Enforcement** engine to process massive invoices (50+ pages) without hallucination or truncation.

## 🚀 Key Features

- **Page-by-Page Extraction:** Uses `pypdf` to split large documents and process them individually, ensuring 100% data coverage.
- **Strict Schema Validation:** Enforces specific Pydantic models to prevent "Invalid JSON" errors.
- **Auto-Correction:** Automatically fills missing numeric fields with `0.0` to prevent validation crashes.
- **Smart Repair:** Includes logic to fix truncated JSON responses from the LLM.
- **Security:** Uses Environment Variables for API keys.

## 🛠️ Tech Stack

- **Framework:** FastAPI (Python)
- **AI Model:** Gemini 2.0 Flash (via `google-generativeai`)
- **PDF Processing:** PyPDF
- **Validation:** Pydantic

## ⚙️ Setup & Installation

1. **Clone the repository**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/bill-extractor.git](https://github.com/YOUR_USERNAME/bill-extractor.git)
   cd bill-extractor
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**

   Create a .env file in the root directory:
   ```ini
   GEMINI_API_KEY=your_google_api_key_here
   ```

4. **Run the Server**
   ```bash
   python main.py
   ```
   The API will start at:
   ```
   http://localhost:3000
   ```

## 🧪 API Usage

### Endpoint ```POST /extract-bill-data```
### Request Body
```json
{
    "document": "[https://hackrx.blob.core.windows.net/sample_bill.pdf](https://hackrx.blob.core.windows.net/sample_bill.pdf)"
}
```
### Success Response (200 OK)
```json
{
    "is_success": true,
    "token_usage": {
        "total_tokens": 1500,
        "input_tokens": 1000,
        "output_tokens": 500
    },
    "data": {
        "pagewise_line_items": [
            {
                "page_no": "1",
                "page_type": "Bill Detail",
                "bill_items": [
                    {
                        "item_name": "Product A",
                        "item_amount": 100.0,
                        "item_rate": 10.0,
                        "item_quantity": 10.0
                    }
                ]
            }
        ],
        "total_item_count": 1
    }
}
```



## 🧮 Note on Bill Totals

### ❌ The API does not return a `total_bill_amount` field.
This is per the HackRx Datathon rules.

---

### ✔️ Final Total = **Sum of all `item_amount` fields`**  
across all pages and all extracted line items.

---

### 🛑 Double-Counting Prevention

The engine automatically **ignores summary pages** such as:

- Final Bill  
- Total Summary  
- Grand Total  
- Consolidated Charges  

unless they contain **new, unique** line items.

This ensures that the computed sum is **accurate** and does **not** double-count repeated totals.



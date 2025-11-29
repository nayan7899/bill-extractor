from pydantic import BaseModel
from typing import List, Literal, Optional

class ExtractRequest(BaseModel):
    document: str 

class TokenUsage(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int

class BillItem(BaseModel):
    item_name: str
    item_amount: float
    item_rate: float
    item_quantity: float

class PageData(BaseModel):
    page_no: str
    page_type: Literal["Bill Detail", "Final Bill", "Pharmacy"]
    bill_items: List[BillItem]

class ExtractionData(BaseModel):
    pagewise_line_items: List[PageData]
    total_item_count: int

class APIResponse(BaseModel):
    is_success: bool
    token_usage: Optional[TokenUsage] = None 
    data: Optional[ExtractionData] = None
    message: Optional[str] = None
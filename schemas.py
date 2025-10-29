"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- Invoice -> "invoice" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import date

# ----------------------
# App-specific schemas
# ----------------------

class InvoiceItem(BaseModel):
    description: str = Field(..., description="Item or service description")
    quantity: float = Field(1, ge=0, description="Quantity")
    unit_price: float = Field(..., ge=0, description="Price per unit")

class Invoice(BaseModel):
    """
    Invoices collection schema
    Collection name: "invoice" (lowercase of class name)
    """
    customer_name: str = Field(..., description="Customer full name")
    customer_email: EmailStr = Field(..., description="Customer email for sharing link")
    customer_address: Optional[str] = Field(None, description="Customer address")
    invoice_number: Optional[str] = Field(None, description="Optional human-friendly invoice number")
    issue_date: date = Field(..., description="Date the invoice was issued")
    due_date: Optional[date] = Field(None, description="Payment due date")
    currency: str = Field("USD", description="Currency code like USD, EUR")
    items: List[InvoiceItem] = Field(default_factory=list, description="Line items")
    notes: Optional[str] = Field(None, description="Additional notes or terms")
    status: str = Field("unpaid", description="unpaid | paid | overdue | cancelled")
    subtotal: float = Field(..., ge=0, description="Sum of line items (quantity * unit_price)")
    tax: float = Field(0, ge=0, description="Tax amount")
    discount: float = Field(0, ge=0, description="Discount amount")
    total: float = Field(..., ge=0, description="Grand total after taxes and discounts")

# You can keep example schemas below if needed for reference
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True

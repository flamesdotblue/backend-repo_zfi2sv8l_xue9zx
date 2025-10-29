import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Invoice, InvoiceItem

app = FastAPI(title="Invoice Link Sharing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers
class ObjectIdStr(str):
    @classmethod
    def validate(cls, v):
        try:
            ObjectId(str(v))
            return str(v)
        except Exception:
            raise ValueError("Invalid ObjectId")


def serialize_invoice(doc: dict) -> dict:
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id")) if doc.get("_id") else None
    # Convert dates to ISO format strings
    for key in ["issue_date", "due_date", "created_at", "updated_at"]:
        if key in doc and hasattr(doc[key], "isoformat"):
            doc[key] = doc[key].isoformat()
    return doc


@app.get("/")
def read_root():
    return {"message": "Invoice Link Sharing Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
            except Exception:
                pass
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Request models
class CreateInvoiceRequest(Invoice):
    pass

class CreateInvoiceResponse(BaseModel):
    id: str
    share_url: str


@app.post("/api/invoices", response_model=CreateInvoiceResponse)
def create_invoice(payload: CreateInvoiceRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    data = payload.model_dump()

    # Compute totals server-side as safety
    subtotal = sum([(item["quantity"] * item["unit_price"]) for item in data.get("items", [])])
    data["subtotal"] = round(subtotal, 2)
    total = subtotal + float(data.get("tax", 0)) - float(data.get("discount", 0))
    data["total"] = round(max(total, 0), 2)

    inserted_id = create_document("invoice", data)

    backend_url = os.getenv("BACKEND_URL") or ""
    # Prefer VITE_BACKEND_URL on the frontend to construct links. For API we expose path.
    share_url = f"/public/invoices/{inserted_id}"

    return CreateInvoiceResponse(id=inserted_id, share_url=share_url)


@app.get("/api/invoices")
def list_invoices(limit: Optional[int] = 50):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    docs = get_documents("invoice", {}, limit=limit)
    return [serialize_invoice(d) for d in docs]


@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    try:
        oid = ObjectId(invoice_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid invoice id")
    doc = db["invoice"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return serialize_invoice(doc)


# Public endpoint for customers to view invoice by link
@app.get("/public/invoices/{invoice_id}")
def public_invoice(invoice_id: str):
    try:
        oid = ObjectId(invoice_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid invoice id")
    doc = db["invoice"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    # Return a safe subset for public view
    doc = serialize_invoice(doc)
    return {
        "id": doc.get("id"),
        "invoice_number": doc.get("invoice_number"),
        "customer_name": doc.get("customer_name"),
        "customer_email": doc.get("customer_email"),
        "customer_address": doc.get("customer_address"),
        "issue_date": doc.get("issue_date"),
        "due_date": doc.get("due_date"),
        "currency": doc.get("currency"),
        "items": doc.get("items", []),
        "notes": doc.get("notes"),
        "status": doc.get("status"),
        "subtotal": doc.get("subtotal"),
        "tax": doc.get("tax"),
        "discount": doc.get("discount"),
        "total": doc.get("total"),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

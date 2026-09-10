from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Product,
    ProductDocument,
    ProductDocumentChunk,
    ProductEvidence,
    ProductEvidenceLocation,
)
from app.schemas import (
    EvidenceStatusResponse,
    DocumentParseResponse,
    ProductDocumentChunkOut,
    ProductDocumentOut,
    ProductEvidenceLocationOut,
    ProductEvidenceOut,
)
from app.services.evidence_service import ingest_documents

router = APIRouter(prefix="/api", tags=["evidence"])


@router.get("/evidence/status", response_model=EvidenceStatusResponse)
def evidence_status(db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    evidence_records = db.query(ProductEvidence).count()
    products_with_evidence = (
        db.query(ProductEvidence.product_id)
        .distinct()
        .count()
    )

    return {
        "total_products": total_products,
        "products_with_evidence": products_with_evidence,
        "evidence_records": evidence_records,
        "verified_records": db.query(ProductEvidence).filter(
            ProductEvidence.verification_status == "verified"
        ).count(),
        "inferred_records": db.query(ProductEvidence).filter(
            ProductEvidence.verification_status == "inferred"
        ).count(),
        "conflicting_records": db.query(ProductEvidence).filter(
            ProductEvidence.verification_status == "conflicting"
        ).count(),
        "discovered_documents": db.query(ProductDocument).count(),
        "parsed_documents": db.query(ProductDocument).filter(
            ProductDocument.status == "parsed"
        ).count(),
        "document_chunks": db.query(ProductDocumentChunk).count(),
        "document_verified_records": db.query(ProductEvidence).filter(
            ProductEvidence.document_id.is_not(None),
            ProductEvidence.verification_status == "verified",
        ).count(),
    }


@router.get(
    "/products/{product_id}/documents",
    response_model=list[ProductDocumentOut],
)
def product_documents(
    product_id: int,
    db: Session = Depends(get_db),
):
    if not db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    return (
        db.query(ProductDocument)
        .filter(ProductDocument.product_id == product_id)
        .order_by(
            ProductDocument.is_primary.desc(),
            ProductDocument.document_type,
            ProductDocument.title,
        )
        .all()
    )


@router.get(
    "/products/{product_id}/evidence",
    response_model=list[ProductEvidenceOut],
)
def product_evidence(
    product_id: int,
    field: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    query = db.query(ProductEvidence).filter(
        ProductEvidence.product_id == product_id
    )

    if field:
        query = query.filter(ProductEvidence.field_name == field)
    if status:
        query = query.filter(
            ProductEvidence.verification_status == status
        )

    return query.order_by(
        ProductEvidence.field_name,
        ProductEvidence.confidence.desc(),
    ).all()



@router.get(
    "/documents/{document_id}/chunks",
    response_model=list[ProductDocumentChunkOut],
)
def document_chunks(
    document_id: int,
    page: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if not db.get(ProductDocument, document_id):
        raise HTTPException(status_code=404, detail="Document not found")

    query = db.query(ProductDocumentChunk).filter(
        ProductDocumentChunk.document_id == document_id
    )
    if page is not None:
        query = query.filter(ProductDocumentChunk.page_number == page)

    return (
        query.order_by(
            ProductDocumentChunk.page_number,
            ProductDocumentChunk.chunk_index,
        )
        .limit(limit)
        .all()
    )


@router.get(
    "/evidence/{evidence_id}/locations",
    response_model=list[ProductEvidenceLocationOut],
)
def evidence_locations(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    if not db.get(ProductEvidence, evidence_id):
        raise HTTPException(status_code=404, detail="Evidence not found")

    return (
        db.query(ProductEvidenceLocation)
        .filter(ProductEvidenceLocation.evidence_id == evidence_id)
        .order_by(ProductEvidenceLocation.page_number)
        .all()
    )


@router.post(
    "/documents/{document_id}/parse",
    response_model=DocumentParseResponse,
)
async def parse_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    if not db.get(ProductDocument, document_id):
        raise HTTPException(status_code=404, detail="Document not found")

    return await ingest_documents(
        db,
        document_id=document_id,
        limit=1,
    )

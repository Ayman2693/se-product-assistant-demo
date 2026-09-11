from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db import get_db
from app.models import Product, ProductFamily, ProductFamilyMember
from app.routers.products import serialize_product
from app.schemas import (
    FamilyStatusOut,
    ProductFamilyDetailOut,
    ProductFamilySummaryOut,
    ProductKnowledgeGraphOut,
)
from app.services.family_graph import (
    build_product_knowledge_graph,
    family_status,
    rebuild_family_graph,
)

router = APIRouter(prefix="/api", tags=["knowledge"])


def _family_summary(family: ProductFamily) -> dict:
    verified_members = [
        membership
        for membership in family.memberships
        if membership.verification_status == "verified"
    ]
    return {
        "id": family.id,
        "name": family.name,
        "manufacturer": family.manufacturer,
        "category": family.category or "",
        "verification_status": family.verification_status,
        "source_type": family.source_type,
        "confidence": family.confidence,
        "member_count": len(verified_members),
    }


@router.get("/families/status", response_model=FamilyStatusOut)
def get_family_status(db: Session = Depends(get_db)):
    return family_status(db)


@router.get("/families", response_model=list[ProductFamilySummaryOut])
def list_families(
    q: str | None = Query(default=None),
    manufacturer: str | None = Query(default=None),
    min_members: int = Query(default=1, ge=1, le=1000),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = (
        db.query(ProductFamily)
        .options(selectinload(ProductFamily.memberships))
        .filter(ProductFamily.verification_status == "verified")
    )

    if manufacturer:
        query = query.filter(ProductFamily.manufacturer == manufacturer)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            ProductFamily.name.ilike(like),
            ProductFamily.manufacturer.ilike(like),
            ProductFamily.category.ilike(like),
        ))

    families = query.order_by(
        ProductFamily.manufacturer,
        ProductFamily.name,
    ).all()

    rows = [
        _family_summary(family)
        for family in families
    ]
    rows = [
        row
        for row in rows
        if row["member_count"] >= min_members
    ]
    return rows[:limit]


@router.get("/families/{family_id}", response_model=ProductFamilyDetailOut)
def get_family(family_id: int, db: Session = Depends(get_db)):
    family = (
        db.query(ProductFamily)
        .options(
            selectinload(ProductFamily.memberships)
            .joinedload(ProductFamilyMember.product)
        )
        .filter(ProductFamily.id == family_id)
        .first()
    )
    if not family:
        raise HTTPException(status_code=404, detail="Product family not found")

    result = _family_summary(family)
    result["members"] = [
        {
            "product": serialize_product(membership.product),
            "verification_status": membership.verification_status,
            "source_type": membership.source_type,
            "source_text": membership.source_text or "",
            "confidence": membership.confidence,
        }
        for membership in sorted(
            family.memberships,
            key=lambda item: item.product.part_number,
        )
        if membership.verification_status == "verified"
    ]
    return result


@router.get(
    "/products/{product_id}/knowledge-graph",
    response_model=ProductKnowledgeGraphOut,
)
def product_knowledge_graph(product_id: int, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .options(
            joinedload(Product.features),
            selectinload(Product.documents),
        )
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return build_product_knowledge_graph(db, product)


@router.post("/families/rebuild", response_model=FamilyStatusOut)
def rebuild_families(db: Session = Depends(get_db)):
    stats = rebuild_family_graph(db)
    db.commit()
    return {
        "families": stats["families"],
        "verified_memberships": stats["verified_memberships"],
        "multi_sku_families": stats["multi_sku_families"],
    }

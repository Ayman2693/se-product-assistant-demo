from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Product,
    ProductFamily,
    ProductFamilyMember,
)


_AUTO_SOURCES = {
    "structured_family_field",
    "catalog_explicit",
    "document_explicit",
}

# Deliberately requires the characteristic electronics family shape "ABC-X2".
# This prevents unrelated prose such as "Bluetooth family" or chipset families
# without a compatible SE product prefix from becoming customer-facing groups.
_FAMILY_TOKEN = r"[A-Z][A-Z0-9]{1,15}-[A-Z0-9]{1,10}"
_FAMILY_PATTERNS = [
    re.compile(rf"(?<![A-Z0-9])({_FAMILY_TOKEN})\s+(?:series|family)\b", re.I),
    re.compile(rf"\b(?:series|family)\s+({_FAMILY_TOKEN})(?![A-Z0-9])", re.I),
]


@dataclass(frozen=True)
class FamilyMention:
    name: str
    source_type: str
    source_text: str
    confidence: float


def normalize_family_name(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


def _sku_compatible(product: Product, family_name: str) -> bool:
    """
    Validation, not derivation: an explicitly stated family must actually be
    a prefix of the SKU it is being attached to.

    We never derive a family by truncating a SKU.
    """
    family = normalize_family_name(family_name)
    sku = normalize_family_name(product.part_number)

    if not family or not sku:
        return False
    if len(family) >= len(sku):
        return False
    return sku.startswith(family)


def _explicit_mentions_from_text(
    product: Product,
    text: str,
    source_type: str,
    confidence: float,
) -> list[FamilyMention]:
    mentions: list[FamilyMention] = []
    for pattern in _FAMILY_PATTERNS:
        for match in pattern.finditer(text or ""):
            name = normalize_family_name(match.group(1))
            if _sku_compatible(product, name):
                mentions.append(
                    FamilyMention(
                        name=name,
                        source_type=source_type,
                        source_text=match.group(0).strip()[:500],
                        confidence=confidence,
                    )
                )
    return mentions


def explicit_family_mentions(product: Product) -> list[FamilyMention]:
    """
    Extract only explicit family/series statements.

    Priority:
      1. structured family/series field already present in raw catalog data
      2. linked document title that explicitly says "... series/family"
      3. product catalog description
      4. catalog tags

    Part-number prefix heuristics are intentionally NOT used.
    """
    mentions: list[FamilyMention] = []

    raw: dict[str, Any] = {}
    if product.features:
        try:
            raw = json.loads(product.features.raw_features_json or "{}")
        except Exception:
            raw = {}

    for key in ("product_family", "family", "series", "product_series"):
        value = raw.get(key)
        if not isinstance(value, str):
            continue
        name = normalize_family_name(value)
        if re.fullmatch(_FAMILY_TOKEN, name, re.I) and _sku_compatible(product, name):
            mentions.append(
                FamilyMention(
                    name=name,
                    source_type="structured_family_field",
                    source_text=f"{key}={value}"[:500],
                    confidence=1.0,
                )
            )

    for document in product.documents or []:
        mentions.extend(
            _explicit_mentions_from_text(
                product,
                document.title or "",
                "document_explicit",
                0.99,
            )
        )

    mentions.extend(
        _explicit_mentions_from_text(
            product,
            product.description or "",
            "catalog_explicit",
            0.97,
        )
    )

    try:
        tags = json.loads(product.tags_json or "[]")
    except Exception:
        tags = []

    for tag in tags if isinstance(tags, list) else []:
        mentions.extend(
            _explicit_mentions_from_text(
                product,
                str(tag),
                "catalog_explicit",
                0.96,
            )
        )

    # Keep the strongest provenance for each explicit family name.
    best: dict[str, FamilyMention] = {}
    for mention in mentions:
        previous = best.get(mention.name)
        if previous is None or mention.confidence > previous.confidence:
            best[mention.name] = mention

    return sorted(
        best.values(),
        key=lambda item: (-item.confidence, item.name),
    )


def rebuild_family_graph(db: Session) -> dict:
    """
    Rebuild auto-derived family memberships from explicit evidence only.

    Manual curated rows, if introduced later, are preserved.
    """
    db.query(ProductFamilyMember).filter(
        ProductFamilyMember.source_type.in_(_AUTO_SOURCES)
    ).delete(synchronize_session=False)
    db.flush()

    products = (
        db.query(Product)
        .options(
            joinedload(Product.features),
            selectinload(Product.documents),
        )
        .all()
    )

    discovered: dict[tuple[str, str, int], tuple[Product, FamilyMention]] = {}

    for product in products:
        for mention in explicit_family_mentions(product):
            key = (
                (product.manufacturer or "").strip().lower(),
                mention.name,
                product.id,
            )
            previous = discovered.get(key)
            if previous is None or mention.confidence > previous[1].confidence:
                discovered[key] = (product, mention)

    family_cache: dict[tuple[str, str], ProductFamily] = {}
    family_source_strength: dict[int, float] = {}

    for product, mention in discovered.values():
        manufacturer = (product.manufacturer or "Unknown").strip()
        family_key = (manufacturer.lower(), mention.name)

        family = family_cache.get(family_key)
        if family is None:
            family = (
                db.query(ProductFamily)
                .filter(
                    ProductFamily.manufacturer == manufacturer,
                    ProductFamily.normalized_name == mention.name,
                )
                .first()
            )

        if family is None:
            family = ProductFamily(
                manufacturer=manufacturer,
                name=mention.name,
                normalized_name=mention.name,
                category=product.category or "",
                verification_status="verified",
                source_type=mention.source_type,
                source_text=mention.source_text,
                confidence=mention.confidence,
            )
            db.add(family)
            db.flush()
        else:
            # Existing auto families are updated if stronger explicit evidence
            # is now available. Manual-curated families are never overwritten.
            if (
                family.source_type != "manual_curated"
                and mention.confidence > float(family.confidence or 0.0)
            ):
                family.source_type = mention.source_type
                family.source_text = mention.source_text
                family.confidence = mention.confidence
                family.verification_status = "verified"

            if not family.category:
                family.category = product.category or ""

        family_cache[family_key] = family
        family_source_strength[family.id] = max(
            family_source_strength.get(family.id, 0.0),
            mention.confidence,
        )

        db.add(
            ProductFamilyMember(
                family=family,
                product=product,
                verification_status="verified",
                source_type=mention.source_type,
                source_text=mention.source_text,
                confidence=mention.confidence,
            )
        )

    db.flush()

    # Remove stale empty auto families. Manually curated families are retained.
    stale = (
        db.query(ProductFamily)
        .filter(ProductFamily.source_type != "manual_curated")
        .all()
    )
    for family in stale:
        if not family.memberships:
            db.delete(family)

    db.flush()

    family_count = db.query(ProductFamily).count()
    membership_count = db.query(ProductFamilyMember).filter(
        ProductFamilyMember.verification_status == "verified"
    ).count()

    useful_family_count = sum(
        1
        for family in db.query(ProductFamily).options(selectinload(ProductFamily.memberships)).all()
        if sum(
            1
            for membership in family.memberships
            if membership.verification_status == "verified"
        ) >= 2
    )

    return {
        "families": family_count,
        "verified_memberships": membership_count,
        "multi_sku_families": useful_family_count,
        "products_scanned": len(products),
    }


def _verified_family_memberships_for_products(
    db: Session,
    product_ids: list[int],
) -> dict[int, list[ProductFamilyMember]]:
    if not product_ids:
        return {}

    memberships = (
        db.query(ProductFamilyMember)
        .options(
            joinedload(ProductFamilyMember.family),
        )
        .filter(
            ProductFamilyMember.product_id.in_(product_ids),
            ProductFamilyMember.verification_status == "verified",
            ProductFamily.verification_status == "verified",
        )
        .join(ProductFamily, ProductFamily.id == ProductFamilyMember.family_id)
        .all()
    )

    by_product: dict[int, list[ProductFamilyMember]] = {}
    for membership in memberships:
        by_product.setdefault(membership.product_id, []).append(membership)
    return by_product


def family_summaries_for_products(
    db: Session,
    product_ids: list[int],
) -> dict[int, dict]:
    """
    Return one customer-safe family only when the product has an unambiguous
    verified explicit membership.
    """
    by_product = _verified_family_memberships_for_products(db, product_ids)

    family_ids = {
        membership.family_id
        for memberships in by_product.values()
        for membership in memberships
    }

    counts: dict[int, int] = {}
    if family_ids:
        rows = (
            db.query(ProductFamilyMember)
            .filter(
                ProductFamilyMember.family_id.in_(family_ids),
                ProductFamilyMember.verification_status == "verified",
            )
            .all()
        )
        for row in rows:
            counts[row.family_id] = counts.get(row.family_id, 0) + 1

    result: dict[int, dict] = {}
    for product_id, memberships in by_product.items():
        distinct = {membership.family_id: membership for membership in memberships}
        if len(distinct) != 1:
            # Ambiguous explicit memberships are safer left ungrouped.
            continue

        membership = next(iter(distinct.values()))
        family = membership.family
        result[product_id] = {
            "id": family.id,
            "name": family.name,
            "manufacturer": family.manufacturer,
            "category": family.category or "",
            "verification_status": family.verification_status,
            "source_type": membership.source_type,
            "confidence": membership.confidence,
            "member_count": counts.get(family.id, 1),
        }

    return result


def annotate_results_with_families(
    db: Session,
    results: list[dict],
) -> list[dict]:
    product_ids = [
        row.get("product", {}).get("id")
        for row in results
        if row.get("product", {}).get("id") is not None
    ]
    summaries = family_summaries_for_products(db, product_ids)

    for row in results:
        product_id = row.get("product", {}).get("id")
        row["family"] = summaries.get(product_id)

    return results


def family_status(db: Session) -> dict:
    families = db.query(ProductFamily).count()
    memberships = db.query(ProductFamilyMember).filter(
        ProductFamilyMember.verification_status == "verified"
    ).count()

    grouped = 0
    for family in (
        db.query(ProductFamily)
        .options(selectinload(ProductFamily.memberships))
        .all()
    ):
        verified = [
            member
            for member in family.memberships
            if member.verification_status == "verified"
        ]
        if len(verified) >= 2:
            grouped += 1

    return {
        "families": families,
        "verified_memberships": memberships,
        "multi_sku_families": grouped,
    }


def build_product_knowledge_graph(db: Session, product: Product) -> dict:
    """
    Virtual graph view over existing normalized data.

    Only explicit family membership is shown as verified. Technologies extracted
    from catalog text remain marked inferred. Linked documents are represented
    as provenance nodes, not as proof that every document statement applies to
    the exact SKU.
    """
    nodes: list[dict] = []
    edges: list[dict] = []

    product_node = f"product:{product.id}"
    nodes.append({
        "id": product_node,
        "type": "product",
        "label": product.part_number,
        "data": {
            "manufacturer": product.manufacturer,
            "category": product.category,
            "url": product.product_url or "",
        },
    })

    families = family_summaries_for_products(db, [product.id])
    family = families.get(product.id)
    if family:
        family_node = f"family:{family['id']}"
        nodes.append({
            "id": family_node,
            "type": "family",
            "label": family["name"],
            "data": family,
        })
        edges.append({
            "source": product_node,
            "target": family_node,
            "type": "member_of",
            "verification_status": "verified",
            "source_type": family["source_type"],
        })

    technologies: list[str] = []
    if product.features:
        try:
            technologies = json.loads(product.features.technologies_json or "[]")
        except Exception:
            technologies = []

    for technology in technologies:
        node_id = f"technology:{str(technology).lower()}"
        nodes.append({
            "id": node_id,
            "type": "technology",
            "label": str(technology),
            "data": {},
        })
        edges.append({
            "source": product_node,
            "target": node_id,
            "type": "supports",
            "verification_status": "inferred",
            "source_type": "catalog_feature_extraction",
        })

    for document in product.documents or []:
        node_id = f"document:{document.id}"
        nodes.append({
            "id": node_id,
            "type": "document",
            "label": document.title or document.document_type,
            "data": {
                "document_type": document.document_type,
                "url": document.url,
                "status": document.status,
            },
        })
        edges.append({
            "source": product_node,
            "target": node_id,
            "type": "documented_by",
            "verification_status": "verified",
            "source_type": "document_link",
        })

    # De-duplicate shared technology nodes.
    unique_nodes = {node["id"]: node for node in nodes}

    return {
        "product_id": product.id,
        "nodes": list(unique_nodes.values()),
        "edges": edges,
    }

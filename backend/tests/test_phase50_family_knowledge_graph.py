import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductDocument, ProductFamily, ProductFamilyMember, ProductFeature
from app.services.family_graph import (
    annotate_results_with_families,
    build_product_knowledge_graph,
    explicit_family_mentions,
    rebuild_family_graph,
)


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _product(
    db,
    pn,
    *,
    description="",
    manufacturer="u-blox",
    category="Wireless Modules",
    tags=None,
    raw=None,
):
    product = Product(
        part_number=pn,
        manufacturer=manufacturer,
        category=category,
        description=description,
        tags_json=json.dumps(tags or []),
    )
    db.add(product)
    db.flush()
    db.add(ProductFeature(
        product_id=product.id,
        technologies_json='["bluetooth"]',
        raw_features_json=json.dumps(raw or {}),
    ))
    db.flush()
    return product


def test_part_number_prefix_alone_never_creates_family():
    db = _db()
    product = _product(db, "NORA-B206-00B", description="Bluetooth LE module")
    assert explicit_family_mentions(product) == []


def test_explicit_series_in_catalog_text_creates_verified_membership():
    db = _db()
    product = _product(
        db,
        "NORA-B206-00B",
        description="Member of the NORA-B2 series for Bluetooth LE applications.",
    )

    mentions = explicit_family_mentions(product)
    assert len(mentions) == 1
    assert mentions[0].name == "NORA-B2"
    assert mentions[0].source_type == "catalog_explicit"


def test_unrelated_chip_family_is_rejected_for_product_membership():
    db = _db()
    product = _product(
        db,
        "NORA-B206-00B",
        description="Uses the NRF54-L1 series chipset.",
    )
    assert explicit_family_mentions(product) == []


def test_explicit_document_series_title_is_accepted():
    db = _db()
    product = _product(db, "MAYA-W266-00B")
    db.add(ProductDocument(
        product_id=product.id,
        document_type="datasheet",
        title="MAYA-W2 series data sheet",
        url="https://example.com/maya-w2.pdf",
        status="parsed",
    ))
    db.flush()

    # Relationship collection is loaded for the in-memory test object.
    db.refresh(product)
    mentions = explicit_family_mentions(product)

    assert any(
        mention.name == "MAYA-W2" and mention.source_type == "document_explicit"
        for mention in mentions
    )


def test_rebuild_groups_only_explicit_family_members():
    db = _db()
    _product(
        db,
        "NORA-B201-00B",
        description="NORA-B2 series Bluetooth module",
    )
    _product(
        db,
        "NORA-B206-00B",
        description="NORA-B2 series Bluetooth module with internal antenna",
    )
    _product(
        db,
        "NORA-B216-00B",
        description="Bluetooth module without an explicit family statement",
    )
    db.commit()

    stats = rebuild_family_graph(db)
    db.commit()

    assert stats["families"] == 1
    assert stats["verified_memberships"] == 2
    assert stats["multi_sku_families"] == 1

    family = db.query(ProductFamily).one()
    assert family.name == "NORA-B2"
    assert {
        membership.product.part_number
        for membership in family.memberships
    } == {"NORA-B201-00B", "NORA-B206-00B"}


def test_match_annotation_is_customer_safe_and_verified_only():
    db = _db()
    p1 = _product(db, "NORA-B201-00B", description="NORA-B2 series module")
    p2 = _product(db, "NORA-B206-00B", description="NORA-B2 series module")
    db.commit()
    rebuild_family_graph(db)
    db.commit()

    results = [
        {"product": {"id": p1.id, "part_number": p1.part_number}},
        {"product": {"id": p2.id, "part_number": p2.part_number}},
    ]
    annotate_results_with_families(db, results)

    assert results[0]["family"]["name"] == "NORA-B2"
    assert results[0]["family"]["verification_status"] == "verified"
    assert results[0]["family"]["member_count"] == 2


def test_virtual_knowledge_graph_marks_family_verified_and_technology_inferred():
    db = _db()
    product = _product(
        db,
        "NORA-B206-00B",
        description="NORA-B2 series Bluetooth module",
    )
    db.commit()
    rebuild_family_graph(db)
    db.commit()

    graph = build_product_knowledge_graph(db, product)

    member_edge = next(edge for edge in graph["edges"] if edge["type"] == "member_of")
    technology_edge = next(edge for edge in graph["edges"] if edge["type"] == "supports")

    assert member_edge["verification_status"] == "verified"
    assert technology_edge["verification_status"] == "inferred"

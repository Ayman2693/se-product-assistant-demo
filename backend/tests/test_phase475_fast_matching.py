from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductFeature
from app.routers.products import (
    _load_match_candidates,
    _technical_evidence_pool,
)
from app.schemas import MatchRequest


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def _add_product(db, pn, category, technologies=None, wifi_generation=None, has_bluetooth=None, has_gnss=None):
    product = Product(
        part_number=pn,
        manufacturer="Test",
        category=category,
        description="test product",
        tags_json="[]",
    )
    db.add(product)
    db.flush()
    db.add(ProductFeature(
        product_id=product.id,
        technologies_json=str(technologies or []).replace("'", '"'),
        wifi_generation=wifi_generation,
        has_bluetooth=has_bluetooth,
        has_gnss=has_gnss,
        raw_features_json="{}",
    ))
    return product


def test_category_prefilter_reduces_catalog_without_losing_target_category():
    _, db = _session()
    for i in range(40):
        _add_product(db, f"WIFI-{i}", "Wi-Fi Modules", technologies=["wifi"], wifi_generation="6")
    for i in range(12):
        _add_product(db, f"CAP-{i}", "Capacitors")
    db.commit()

    req = MatchRequest(catalog_category="Capacitors")
    rows = _load_match_candidates(db, req)

    assert len(rows) == 12
    assert all("capacitor" in p.category.lower() for p in rows)


def test_wifi_prefilter_keeps_wifi_candidates_only_as_sql_superset():
    _, db = _session()
    for i in range(20):
        _add_product(db, f"WIFI-{i}", "Wireless Modules", technologies=["wifi"], wifi_generation="6")
    for i in range(20):
        _add_product(db, f"SENSOR-{i}", "Pressure Sensors")
    db.commit()

    req = MatchRequest(technologies=["wifi"])
    rows = _load_match_candidates(db, req)

    assert len(rows) == 20
    assert all(p.features.wifi_generation == "6" for p in rows)


def test_eager_load_avoids_n_plus_one_feature_queries():
    engine, db = _session()
    for i in range(30):
        _add_product(db, f"WIFI-{i}", "Wireless Modules", technologies=["wifi"], wifi_generation="5")
    db.commit()

    statements = []
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    rows = _load_match_candidates(db, MatchRequest(technologies=["wifi"]))

    # Access the relationship for every row; contains_eager should prevent
    # an additional SELECT per product.
    assert all(p.features is not None for p in rows)
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) == 1


def test_evidence_pool_keeps_every_product_tied_at_top10_cutoff():
    scored = []
    for index in range(20):
        if index < 9:
            score = 100
        elif index < 15:
            score = 90
        else:
            score = 80
        product = Product(
            id=index + 1,
            part_number=f"P-{index}",
            manufacturer="Test",
            category="Test",
        )
        scored.append((product, {"match_percent": score}))

    pool = _technical_evidence_pool(scored, limit=10)

    assert len(pool) == 15
    assert min(score["match_percent"] for _, score in pool) == 90


def test_evidence_pool_drops_products_that_cannot_reach_top10():
    scored = []
    for index, score in enumerate(range(100, 80, -1)):
        product = Product(
            id=index + 1,
            part_number=f"P-{index}",
            manufacturer="Test",
            category="Test",
        )
        scored.append((product, {"match_percent": score}))

    pool = _technical_evidence_pool(scored, limit=10)

    assert len(pool) == 10
    assert [score["match_percent"] for _, score in pool] == list(range(100, 90, -1))

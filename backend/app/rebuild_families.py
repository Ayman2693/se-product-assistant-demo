from app.db import Base, SessionLocal, engine
from app.services.family_graph import rebuild_family_graph


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        stats = rebuild_family_graph(db)
        db.commit()
        print(
            "Family graph rebuilt: "
            f"{stats['families']} explicit families, "
            f"{stats['verified_memberships']} verified memberships, "
            f"{stats['multi_sku_families']} multi-SKU families "
            f"across {stats['products_scanned']} products."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()

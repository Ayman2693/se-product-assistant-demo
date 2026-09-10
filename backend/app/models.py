from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .db import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    part_number = Column(String(180), unique=True, index=True, nullable=False)
    manufacturer = Column(String(120), index=True, nullable=False)
    category = Column(String(180), index=True, nullable=False)
    description = Column(Text, default="")
    tags_json = Column(Text, default="[]")
    product_url = Column(Text, default="")
    lifecycle = Column(String(120), default="Not verified")
    availability = Column(String(180), default="Check live SE page")
    exact = Column(Boolean, default=False)

    features = relationship(
        "ProductFeature",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )

    documents = relationship(
        "ProductDocument",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    evidence = relationship(
        "ProductEvidence",
        back_populates="product",
        cascade="all, delete-orphan",
    )

class ProductFeature(Base):
    __tablename__ = "product_features"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)

    technologies_json = Column(Text, default="[]")
    cellular_class = Column(String(80), nullable=True)
    region = Column(String(80), nullable=True)

    has_gnss = Column(Boolean, nullable=True)
    gnss_precision = Column(String(40), nullable=True)
    wifi_generation = Column(String(40), nullable=True)
    has_bluetooth = Column(Boolean, nullable=True)

    architecture = Column(String(80), nullable=True)
    antenna = Column(String(80), nullable=True)
    form_factor = Column(String(100), nullable=True)

    temperature_min = Column(Float, nullable=True)
    temperature_max = Column(Float, nullable=True)

    certifications_json = Column(Text, default="[]")
    documents_url = Column(Text, default="")
    request_url = Column(Text, default="")
    source_category = Column(String(180), default="")
    source_url = Column(Text, default="")
    imported_live = Column(Boolean, default=False)
    raw_features_json = Column(Text, default="{}")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="features")


class ProductDocument(Base):
    __tablename__ = "product_documents"
    __table_args__ = (
        UniqueConstraint("product_id", "url", name="uq_product_document_url"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    document_type = Column(String(80), default="other", index=True, nullable=False)
    title = Column(String(300), default="", nullable=False)
    url = Column(Text, nullable=False)
    source_page_url = Column(Text, default="")
    mime_type = Column(String(120), nullable=True)
    revision = Column(String(120), nullable=True)
    language = Column(String(40), nullable=True)

    is_primary = Column(Boolean, default=False, nullable=False)
    status = Column(String(40), default="discovered", index=True, nullable=False)

    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="documents")
    evidence = relationship("ProductEvidence", back_populates="document")
    chunks = relationship(
        "ProductDocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class ProductEvidence(Base):
    __tablename__ = "product_evidence"

    id = Column(Integer, primary_key=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id = Column(
        Integer,
        ForeignKey("product_documents.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    field_name = Column(String(120), index=True, nullable=False)
    value_text = Column(Text, default="")
    normalized_value = Column(String(300), nullable=True)

    # verified | inferred | not_verified | conflicting
    verification_status = Column(String(40), default="inferred", index=True, nullable=False)

    # catalog_description | datasheet | integration_manual | user_guide | other
    source_type = Column(String(80), default="catalog_description", index=True, nullable=False)
    source_url = Column(Text, default="")
    source_title = Column(String(300), default="")
    evidence_text = Column(Text, default="")

    confidence = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="evidence")
    document = relationship("ProductDocument", back_populates="evidence")
    locations = relationship(
        "ProductEvidenceLocation",
        back_populates="evidence",
        cascade="all, delete-orphan",
    )


class ProductDocumentChunk(Base):
    __tablename__ = "product_document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "page_number",
            "chunk_index",
            name="uq_document_page_chunk",
        ),
    )

    id = Column(Integer, primary_key=True)
    document_id = Column(
        Integer,
        ForeignKey("product_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    page_number = Column(Integer, index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, default="", nullable=False)
    char_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("ProductDocument", back_populates="chunks")
    evidence_locations = relationship(
        "ProductEvidenceLocation",
        back_populates="chunk",
        cascade="all, delete-orphan",
    )


class ProductEvidenceLocation(Base):
    __tablename__ = "product_evidence_locations"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(
        Integer,
        ForeignKey("product_evidence.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id = Column(
        Integer,
        ForeignKey("product_document_chunks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    page_number = Column(Integer, index=True, nullable=False)
    quote = Column(Text, default="", nullable=False)

    evidence = relationship("ProductEvidence", back_populates="locations")
    chunk = relationship("ProductDocumentChunk", back_populates="evidence_locations")

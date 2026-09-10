from pydantic import BaseModel, Field
from typing import List, Optional

class HealthResponse(BaseModel):
    status: str
    service: str

class ProductFeaturesOut(BaseModel):
    technologies: List[str] = Field(default_factory=list)
    cellular_class: Optional[str] = None
    region: Optional[str] = None
    has_gnss: Optional[bool] = None
    gnss_precision: Optional[str] = None
    wifi_generation: Optional[str] = None
    has_bluetooth: Optional[bool] = None
    architecture: Optional[str] = None
    antenna: Optional[str] = None
    form_factor: Optional[str] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    certifications: List[str] = Field(default_factory=list)
    documents_url: str = ""
    request_url: str = ""
    imported_live: bool = False

class ProductOut(BaseModel):
    id: int
    part_number: str
    manufacturer: str
    category: str
    description: str
    tags: List[str] = Field(default_factory=list)
    product_url: str = ""
    lifecycle: str = ""
    availability: str = ""
    features: Optional[ProductFeaturesOut] = None

class MatchRequest(BaseModel):
    application: Optional[str] = None
    product_domain: Optional[str] = None
    catalog_category: Optional[str] = None
    generic_interface: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    cellular_class: Optional[str] = None
    region: Optional[str] = None
    architecture: Optional[str] = None
    antenna: Optional[str] = None
    wifi_generation: Optional[str] = None
    gnss_precision: Optional[str] = None
    low_power: Optional[bool] = None
    host_interface: Optional[str] = None
    antenna_connector: Optional[str] = None
    antenna_count: Optional[int] = None
    bluetooth_required: Optional[bool] = None
    bluetooth_version_min: Optional[str] = None
    max_footprint_mm2: Optional[float] = None
    form_factor: Optional[str] = None
    gnss_dual_band: Optional[bool] = None
    mandatory: List[str] = Field(default_factory=list)

class MatchCriterionEvidence(BaseModel):
    key: str
    label: str
    requested_value: str
    status: str
    evidence_value: Optional[str] = None
    source_type: Optional[str] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    page_number: Optional[int] = None
    confidence: Optional[float] = None


class MatchEvidenceSummary(BaseModel):
    total: int = 0
    verified: int = 0
    inferred: int = 0
    not_verified: int = 0
    conflicting: int = 0
    evidence_score: int = 0


class MatchResult(BaseModel):
    product: ProductOut
    match_percent: int
    reasons: List[str] = Field(default_factory=list)
    evidence_score: int = 0
    evidence_summary: MatchEvidenceSummary = Field(default_factory=MatchEvidenceSummary)
    criterion_evidence: List[MatchCriterionEvidence] = Field(default_factory=list)

class MatchResponse(BaseModel):
    count: int
    matches: List[MatchResult] = Field(default_factory=list)

class CatalogStatusResponse(BaseModel):
    total_products: int
    structured_products: int
    live_imported_products: int
    catalog_sections_configured: int

class RootResponse(BaseModel):
    name: str
    version: str
    docs: str


class RequirementState(BaseModel):
    application: Optional[str] = None
    product_domain: Optional[str] = None
    catalog_category: Optional[str] = None
    generic_interface: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    cellular_class: Optional[str] = None
    region: Optional[str] = None
    architecture: Optional[str] = None
    antenna: Optional[str] = None
    wifi_generation: Optional[str] = None
    gnss_precision: Optional[str] = None
    low_power: Optional[bool] = None
    host_interface: Optional[str] = None
    antenna_connector: Optional[str] = None
    antenna_count: Optional[int] = None
    bluetooth_required: Optional[bool] = None
    bluetooth_version_min: Optional[str] = None
    max_footprint_mm2: Optional[float] = None
    form_factor: Optional[str] = None
    gnss_dual_band: Optional[bool] = None

class InterpretRequest(BaseModel):
    text: str
    current: Optional[RequirementState] = None

class NextQuestionOut(BaseModel):
    key: str
    text: str
    options: List[str] = Field(default_factory=list)

class InterpretResponse(BaseModel):
    requirements: RequirementState
    evidence: List[str] = Field(default_factory=list)
    confidence: float
    missing: List[str] = Field(default_factory=list)
    next_question: Optional[NextQuestionOut] = None

class NaturalRecommendRequest(BaseModel):
    text: str
    current: Optional[RequirementState] = None

class NaturalRecommendResponse(BaseModel):
    requirements: RequirementState
    evidence: List[str] = Field(default_factory=list)
    confidence: float
    missing: List[str] = Field(default_factory=list)
    next_question: Optional[NextQuestionOut] = None
    ready_to_match: bool
    match: Optional[MatchResponse] = None


class ProductDocumentOut(BaseModel):
    id: int
    product_id: int
    document_type: str
    title: str
    url: str
    source_page_url: str = ""
    mime_type: Optional[str] = None
    revision: Optional[str] = None
    language: Optional[str] = None
    is_primary: bool = False
    status: str


class ProductEvidenceOut(BaseModel):
    id: int
    product_id: int
    document_id: Optional[int] = None
    field_name: str
    value_text: str = ""
    normalized_value: Optional[str] = None
    verification_status: str
    source_type: str
    source_url: str = ""
    source_title: str = ""
    evidence_text: str = ""
    confidence: float


class EvidenceStatusResponse(BaseModel):
    total_products: int
    products_with_evidence: int
    evidence_records: int
    verified_records: int
    inferred_records: int
    conflicting_records: int
    discovered_documents: int
    parsed_documents: int = 0
    document_chunks: int = 0
    document_verified_records: int = 0


class ProductDocumentChunkOut(BaseModel):
    id: int
    document_id: int
    page_number: int
    chunk_index: int
    text: str
    char_count: int


class ProductEvidenceLocationOut(BaseModel):
    id: int
    evidence_id: int
    chunk_id: int
    page_number: int
    quote: str


class DocumentParseResponse(BaseModel):
    documents_requested: int
    documents_parsed: int
    documents_failed: int
    chunks_created: int
    verified_evidence_created: int
    failures: List[dict] = Field(default_factory=list)

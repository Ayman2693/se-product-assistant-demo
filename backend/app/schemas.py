from pydantic import BaseModel, Field
from typing import Any, List, Optional

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
    antenna_applications: List[str] = Field(default_factory=list)
    antenna_bands: List[str] = Field(default_factory=list)
    antenna_active: Optional[bool] = None
    engineering: dict[str, Any] = Field(default_factory=dict)
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    certifications: List[str] = Field(default_factory=list)
    documents_url: str = ""
    request_url: str = ""
    imported_live: bool = False

    # Capacitor-specific structured catalog fields.
    capacitance_uf: Optional[float] = None
    capacitor_voltage_v: Optional[float] = None
    capacitor_tolerance_pct: Optional[float] = None
    capacitor_technology: Optional[str] = None
    capacitor_mounting: Optional[str] = None
    capacitor_case_size: Optional[str] = None
    capacitor_esr_ohm: Optional[float] = None
    capacitor_ripple_current_a: Optional[float] = None
    capacitor_lifetime_h: Optional[int] = None
    capacitor_theoretical_energy_j: Optional[float] = None

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
    wifi_generation: List[str] = Field(default_factory=list)
    gnss_precision: Optional[str] = None
    low_power: Optional[bool] = None
    host_interface: Optional[str] = None
    antenna_connector: Optional[str] = None
    antenna_count: Optional[int] = None
    antenna_application: Optional[str] = None
    antenna_band: Optional[str] = None
    antenna_active: Optional[bool] = None

    # Schema-driven engineering qualification shared by all product categories.
    engineering_requirements: dict[str, Any] = Field(default_factory=dict)
    answered_engineering_fields: List[str] = Field(default_factory=list)

    bluetooth_required: Optional[bool] = None
    bluetooth_version_min: Optional[str] = None
    max_footprint_mm2: Optional[float] = None
    form_factor: Optional[str] = None
    gnss_dual_band: Optional[bool] = None

    # Capacitor qualification. Numeric thresholds use engineering semantics:
    # voltage >= requested minimum, tolerance <= requested maximum, ESR <= max,
    # ripple/lifetime/energy >= requested minimum.
    capacitance_uf: Optional[float] = None
    capacitor_voltage_v: Optional[float] = None
    capacitor_tolerance_pct: Optional[float] = None
    capacitor_technology: Optional[str] = None
    capacitor_mounting: Optional[str] = None
    capacitor_case_size: Optional[str] = None
    capacitor_esr_max_ohm: Optional[float] = None
    capacitor_ripple_current_min_a: Optional[float] = None
    capacitor_lifetime_min_h: Optional[int] = None
    capacitor_temperature_min_c: Optional[float] = None
    capacitor_temperature_max_c: Optional[float] = None
    capacitor_energy_min_j: Optional[float] = None

    mandatory: List[str] = Field(default_factory=list)

    # Optional discriminator fields that the customer explicitly left open
    # (for example "Either connector is acceptable"). This prevents the
    # adaptive engine from asking the same optional question repeatedly.
    answered_open_fields: List[str] = Field(default_factory=list)

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


class ProductFamilySummaryOut(BaseModel):
    id: int
    name: str
    manufacturer: str
    category: str = ""
    verification_status: str
    source_type: str
    confidence: float
    member_count: int = 0


class ProductFamilyMemberOut(BaseModel):
    product: ProductOut
    verification_status: str
    source_type: str
    source_text: str = ""
    confidence: float


class ProductFamilyDetailOut(ProductFamilySummaryOut):
    members: List[ProductFamilyMemberOut] = Field(default_factory=list)


class FamilyStatusOut(BaseModel):
    families: int = 0
    verified_memberships: int = 0
    multi_sku_families: int = 0


class KnowledgeNodeOut(BaseModel):
    id: str
    type: str
    label: str
    data: dict = Field(default_factory=dict)


class KnowledgeEdgeOut(BaseModel):
    source: str
    target: str
    type: str
    verification_status: str
    source_type: str


class ProductKnowledgeGraphOut(BaseModel):
    product_id: int
    nodes: List[KnowledgeNodeOut] = Field(default_factory=list)
    edges: List[KnowledgeEdgeOut] = Field(default_factory=list)


class MatchEvidenceSummary(BaseModel):
    total: int = 0
    verified: int = 0
    inferred: int = 0
    not_verified: int = 0
    conflicting: int = 0
    evidence_score: int = 0


class MatchResult(BaseModel):
    product: ProductOut
    family: Optional[ProductFamilySummaryOut] = None
    match_percent: int
    solution_scope_score: int = 100
    extra_technologies: List[str] = Field(default_factory=list)

    recommendation_confidence: str = "provisional_fit"
    recommendation_confidence_label: str = "Provisional fit"
    verification_required: bool = False
    verification_issues: List[str] = Field(default_factory=list)

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
    category_counts: dict[str, int] = Field(default_factory=dict)
    zero_categories: List[str] = Field(default_factory=list)

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
    wifi_generation: List[str] = Field(default_factory=list)
    gnss_precision: Optional[str] = None
    low_power: Optional[bool] = None
    host_interface: Optional[str] = None
    antenna_connector: Optional[str] = None
    antenna_count: Optional[int] = None
    antenna_application: Optional[str] = None
    antenna_band: Optional[str] = None
    antenna_active: Optional[bool] = None
    bluetooth_required: Optional[bool] = None
    bluetooth_version_min: Optional[str] = None
    max_footprint_mm2: Optional[float] = None
    form_factor: Optional[str] = None
    gnss_dual_band: Optional[bool] = None

    engineering_requirements: dict[str, Any] = Field(default_factory=dict)
    answered_engineering_fields: List[str] = Field(default_factory=list)

    # Capacitor-domain requirement state.
    capacitance_uf: Optional[float] = None
    capacitor_voltage_v: Optional[float] = None
    capacitor_tolerance_pct: Optional[float] = None
    capacitor_tolerance_open: bool = False
    capacitor_technology: Optional[str] = None
    capacitor_mounting: Optional[str] = None
    capacitor_case_size: Optional[str] = None
    capacitor_esr_max_ohm: Optional[float] = None
    capacitor_ripple_current_min_a: Optional[float] = None
    capacitor_lifetime_min_h: Optional[int] = None
    capacitor_temperature_min_c: Optional[float] = None
    capacitor_temperature_max_c: Optional[float] = None
    capacitor_energy_min_j: Optional[float] = None

class AdaptiveQuestionOptionOut(BaseModel):
    label: str
    value: str | bool | List[str]


class AdaptiveQuestionOut(BaseModel):
    key: str
    text: str
    options: List[AdaptiveQuestionOptionOut] = Field(default_factory=list)
    multi_select: bool = False
    required: bool = True
    information_gain: float = 0.0
    known_coverage: float = 0.0
    candidate_count: int = 0
    distinct_known_values: int = 0
    mode: str = "qualification"
    top_tie_count: int = 0


class AdaptiveQuestionRequest(BaseModel):
    requirements: MatchRequest


class AdaptiveQuestionResponse(BaseModel):
    candidate_count: int = 0
    evaluated_fields: int = 0
    question: Optional[AdaptiveQuestionOut] = None


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

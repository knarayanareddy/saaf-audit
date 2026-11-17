from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

from organization import ORG

VALID_STATUSES = {"to_be_scheduled", "in_planning", "in_fieldwork", "in_reporting", "closed"}
VALID_ENTITIES = set(ORG.entity_codes())
VALID_AUDIT_TYPES = set(ORG.audit_types)


class EngagementCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    entity: str
    audit_type: str
    audit_code: Optional[str] = None
    summary: Optional[str] = None
    status: str = "to_be_scheduled"
    lead_auditor: Optional[str] = None
    team_members: list[str] = []
    planning_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    draft_report_date: Optional[str] = None
    final_report_date: Optional[str] = None
    scope_period: Optional[str] = None

    @field_validator('entity')
    @classmethod
    def validate_entity(cls, v: str) -> str:
        if v not in VALID_ENTITIES:
            raise ValueError(f"entity must be one of {sorted(VALID_ENTITIES)}")
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v

    @field_validator('audit_type')
    @classmethod
    def validate_audit_type(cls, v: str) -> str:
        if v not in VALID_AUDIT_TYPES:
            raise ValueError(f"audit_type must be one of {sorted(VALID_AUDIT_TYPES)}")
        return v


class EngagementUpdate(BaseModel):
    name: Optional[str] = None
    entity: Optional[str] = None
    audit_type: Optional[str] = None
    audit_code: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    lead_auditor: Optional[str] = None
    team_members: Optional[list[str]] = None
    jurisdictions: Optional[list[str]] = None
    planning_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    draft_report_date: Optional[str] = None
    final_report_date: Optional[str] = None
    scope_period: Optional[str] = None

    @field_validator('entity')
    @classmethod
    def validate_entity(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ENTITIES:
            raise ValueError(f"entity must be one of {sorted(VALID_ENTITIES)}")
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v

    @field_validator('audit_type')
    @classmethod
    def validate_audit_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_AUDIT_TYPES:
            raise ValueError(f"audit_type must be one of {sorted(VALID_AUDIT_TYPES)}")
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        # An audit without a name cannot be found or told apart in any list; create
        # already requires one, and an edit must not be a way round that.
        if v is None:
            return v
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("name must be 1-500 characters")
        return v


class RunAgentsRequest(BaseModel):
    urls: list[str] = Field(default=[], max_length=10)
    agents: list[str] = ["regulatory", "policy", "interview"]
    use_web_search: bool = True
    custom_queries: list[str] = Field(default=[], max_length=5)
    # None is what the start screen sends for "no keyword"; it must be accepted,
    # or every run without one is rejected before an agent starts.
    manual_keyword: str | None = Field(default="", max_length=200)
    # Free text the auditor adds to the scan's starting context: what they
    # already know that the engagement record does not say.
    extra_context: str = Field(default="", max_length=4000)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=20000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., max_length=50)
    engagement_id: Optional[str] = None
    # How long the reply should be. Chat defaults to brief; the panel's
    # Brief/Detailed switch sends the other value. Affects the chat only —
    # the document-writing agents are unaffected.
    verbosity: Literal["brief", "detailed"] = "brief"


class SummarySuggestRequest(BaseModel):
    name: str
    entity: str
    audit_type: Optional[str] = None


class NameSuggestRequest(BaseModel):
    entity: str
    audit_type: Optional[str] = None
    hint: Optional[str] = None  # optional partial text the user already typed


class ProcessNotesUpdate(BaseModel):
    notes: str


class FrameworkAdd(BaseModel):
    framework_code: str = Field(..., min_length=1, max_length=50)
    framework_name: str = Field(..., min_length=1, max_length=300)
    applicability_rationale: Optional[str] = None
    is_primary: bool = False


class ScopeItemCreate(BaseModel):
    item_type: str = Field(..., pattern="^(in_scope|out_of_scope)$")
    description: str = Field(..., min_length=1, max_length=2000)
    rationale: Optional[str] = None


class QuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1, max_length=2000)
    regulatory_basis: Optional[str] = None


class ImproveTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    field_label: str = Field(default="field", max_length=100)
    instruction: str = Field(default="", max_length=500)
    engagement_id: Optional[str] = None


class ApproveReasoningRequest(BaseModel):
    reasoning: str = Field(..., min_length=1, max_length=20000)


class PatchProcessItemRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    is_included: Optional[bool] = None


class AcceptProcessItemsRequest(BaseModel):
    items: list[dict]  # [{id, name, description, is_included, activities:[...]}]


class Lens4UpdateRequest(BaseModel):
    notes: str = Field("", max_length=5000)
    state: Literal["rich", "partial", "empty"] = "empty"


class ANLPatch(BaseModel):
    background: Optional[str] = None
    objectives: Optional[str] = None
    scope_description: Optional[str] = None
    out_of_scope: Optional[str] = None
    approach: Optional[str] = None
    timing_fieldwork_start: Optional[str] = None
    timing_fieldwork_end: Optional[str] = None
    timing_draft_report: Optional[str] = None
    timing_mgmt_response: Optional[str] = None
    timing_final_report: Optional[str] = None
    responsibility: Optional[str] = None


class RequirementItem(BaseModel):
    id: str
    framework_id: Optional[str] = None
    framework_code: Optional[str] = None
    framework_name: Optional[str] = None
    provision: Optional[str] = None
    what_it_requires: Optional[str] = None
    control_objective: Optional[str] = None
    test_approach: Optional[str] = None
    is_included: bool = True


class FrameworkWithRequirements(BaseModel):
    id: str
    framework_code: str
    framework_name: str
    applicability_rationale: Optional[str] = None
    specific_provision: Optional[str] = None
    source_url: Optional[str] = None
    confidence: Optional[str] = None
    jurisdiction: Optional[str] = None
    is_primary: bool = False
    is_accepted: bool = False
    source: str = "manual"
    requirements: list[RequirementItem] = []


class FrameworkRequirementsResponse(BaseModel):
    status: str
    frameworks: list[FrameworkWithRequirements]

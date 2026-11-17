from typing import Literal
from pydantic import BaseModel, Field


class SourceAnchor(BaseModel):
    section: str = Field(description="Paragraaf- of sectienummer (bijv. §2.3)")
    quote: str = Field(description="Exacte citaat of samenvatting van de bronstekst")


class Control(BaseModel):
    control_id: str = Field(
        description="Unieke ID in formaat POL-{DOMEIN}-{NNN}, bijv. POL-IAM-001"
    )
    domain: str = Field(description="Domein, bijv. IAM, Change, Logging, Vendor Risk")
    who: str = Field(
        description="Verantwoordelijke rol/functie; 'TBD' als niet in beleid"
    )
    what: str = Field(
        description="Control statement: actief en toetsbaar geformuleerd (shall-vorm)"
    )
    why: str = Field(description="Doel/rationale: welk risico wordt gereduceerd")
    when: str = Field(description="Frequentie of trigger; 'TBD' als niet vermeld")
    where: str = Field(
        description="Scope, systemen of processen; 'TBD' als niet vermeld"
    )
    how: str = Field(
        description="Mechanisme/procedure; alleen wat in beleid staat; 'TBD' als niet vermeld"
    )
    source_anchors: list[SourceAnchor] = Field(
        description="Minimaal 1 bronanker per control"
    )
    evidence_hints: list[str] = Field(
        description="Hoog-niveau evidence indicatoren (bijv. 'approval records', 'access logs')"
    )
    confidence: Literal["High", "Medium", "Low"] = Field(
        description=(
            "High = alle 6W's ingevuld + duidelijke bron; "
            "Medium = 1-2 TBD's; "
            "Low = 3+ TBD's of vage tekst"
        )
    )
    open_questions: list[str] = Field(
        description="Ontbrekende informatie voor volledige toetsbaarheid"
    )


class ExtractionResult(BaseModel):
    controls: list[Control]
    document_summary: str = Field(
        description="Korte samenvatting van het beleidsdocument (2-3 zinnen)"
    )
    domain_detected: str = Field(
        description="Gedetecteerd primaire domein op basis van de tekst"
    )

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceField(BaseModel):
    value: Optional[str] = None
    confidence: str = "unknown"
    evidence: Optional[str] = None


class ClientProfile(BaseModel):
    client_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    occupation: Optional[str] = None
    goals: List[str] = Field(default_factory=list)
    risk_tolerance: EvidenceField = Field(default_factory=EvidenceField)
    time_horizon: Dict[str, str] = Field(default_factory=dict)
    liquidity_needs: List[str] = Field(default_factory=list)
    dependents: List[str] = Field(default_factory=list)
    income: Optional[str] = None
    assets: List[str] = Field(default_factory=list)
    liabilities: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    confidence_notes: List[str] = Field(default_factory=list)

    def to_clean_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ClientDocument(BaseModel):
    doc_id: str
    title: str
    text: str
    active: bool = True


class ClientRecord(BaseModel):
    client_id: str
    profile: ClientProfile
    documents: List[ClientDocument] = Field(default_factory=list)

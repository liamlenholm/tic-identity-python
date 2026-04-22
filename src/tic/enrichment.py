from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator

from .data import SigningAuthorityAnalysis
from .models import CamelModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EnrichmentStatus(StrEnum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    PARTIALLY_COMPLETED = "PartiallyCompleted"
    FAILED = "Failed"


class EnrichmentType(StrEnum):
    SPAR = "SPAR"
    COMPANY_ROLES = "CompanyRoles"
    PROPERTY_OWNERSHIP = "PropertyOwnership"
    INCOME = "Income"
    IP_INTELLIGENCE = "IpIntelligence"
    FULL = "Full"


def _normalize_enrichment_status(v: object) -> object:
    if isinstance(v, str):
        mapping = {s.lower(): s for s in EnrichmentStatus}
        return mapping.get(v.lower(), v)
    return v


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class EnrichmentResponse(CamelModel):
    enrichment_id: str
    session_id: str
    status: Annotated[EnrichmentStatus, BeforeValidator(_normalize_enrichment_status)]
    requested_types: list[str]
    completed_types: list[str] = []
    error: str | None = None
    secure_url: str | None = None
    secure_url_expires_at_utc: datetime | None = None


class EnrichmentTypeInfo(CamelModel):
    type: str
    description: str
    enabled: bool


class EnrichmentTypesResponse(CamelModel):
    types: list[EnrichmentTypeInfo] = []
    enabled: bool = False


# ---------------------------------------------------------------------------
# SPAR data (field names match SPAR/Navet column names — NOT camelCase)
# ---------------------------------------------------------------------------


class SparData(BaseModel):
    model_config = {"populate_by_name": True}

    Person_IdNummer: str | None = None
    Person_PersonIdTyp: str | None = None
    Person_SenasteAndringSPAR: str | None = None

    Skydd_Sekretessmarkering: bool | None = None
    Skydd_SkyddadFolkbokforing: bool | None = None
    PersonDetaljer_Sekretessmarkering: bool | None = None

    Namn_Fornamn: str | None = None
    Namn_Mellannamn: str | None = None
    Namn_Efternamn: str | None = None
    Namn_Aviseringsnamn: str | None = None
    Namn_Tilltalsnamn: str | None = None

    PersonDetaljer_Kon: str | None = None
    PersonDetaljer_Fodelsedatum: str | None = None
    PersonDetaljer_Avlidendatum: str | None = None
    PersonDetaljer_Avregistreringsdatum: str | None = None
    PersonDetaljer_AvregistreringsorsakKod: str | None = None
    PersonDetaljer_AvregistreringsorsakBeskrivning: str | None = None

    Folkbokforing_FolkbokfordLanKod: str | None = None
    Folkbokforing_FolkbokfordKommunKod: str | None = None
    Folkbokforing_DistriktKod: str | None = None
    Folkbokforing_Folkbokforingsdatum: str | None = None

    Folkbokforingsadress_SvenskAdress_CareOf: str | None = None
    Folkbokforingsadress_SvenskAdress_Utdelningsadress1: str | None = None
    Folkbokforingsadress_SvenskAdress_Utdelningsadress2: str | None = None
    Folkbokforingsadress_SvenskAdress_PostNr: str | None = None
    Folkbokforingsadress_SvenskAdress_Postort: str | None = None


# ---------------------------------------------------------------------------
# CompanyRoles data (reuses SigningRule, EligiblePerson, SigningAuthorityAnalysis from data.py)
# ---------------------------------------------------------------------------


class CompanyRolesData(CamelModel):
    company_id: int
    company_registration_number: str
    legal_name: str
    legal_entity_type: str
    position_types: list[str] = []
    position_descriptions: list[str] = []
    position_start: str | None = None
    position_end: str | None = None
    company_status: str | None = None
    signature_description: str | None = None
    signing_authority_analysis: SigningAuthorityAnalysis | None = None


# ---------------------------------------------------------------------------
# PropertyOwnership data
# ---------------------------------------------------------------------------


class PropertyOwnershipData(CamelModel):
    fastighet_objekt_identitet: str
    registerbeteckning: str
    andel_taljare: int
    andel_namnare: int
    ownership_start_date: str | None = None


# ---------------------------------------------------------------------------
# Income data (field names match Skatteverket column names)
# ---------------------------------------------------------------------------


class IncomeData(BaseModel):
    model_config = {"populate_by_name": True}

    AR_DEKL: int | None = None
    INK_TJ: int | None = None
    INK_NRV_AKT_TOT: int | None = None
    INK_NRV_PASS_TOT: int | None = None
    USK_NRV_AKT_TOT: int | None = None
    USK_NRV_PASS_TOT: int | None = None
    AVDR_SALLM: int | None = None
    INK_TAX_FORV: int | None = None
    INK_BESK_FORV: int | None = None
    OSKOTT_KAP: int | None = None
    USKOTT_KAP: int | None = None
    SK_SLUT: int | None = None


# ---------------------------------------------------------------------------
# IP Intelligence data
# ---------------------------------------------------------------------------


class IpData(CamelModel):
    ip_address: str
    country_code: str | None = None
    country_name: str | None = None
    isp: str | None = None
    usage_type: str | None = None
    confidence_score: int | None = None
    is_tor: bool = False
    is_likely_vpn: bool = False


class IpOverallRisk(CamelModel):
    level: str
    score: int
    indicators: list[str] = []


class IpIntelligenceData(CamelModel):
    initiating_ip: IpData | None = None
    device_ip: IpData | None = None
    overall_risk: IpOverallRisk | None = None
    enriched_at_utc: datetime | None = None


# ---------------------------------------------------------------------------
# Top-level enrichment data envelope
# ---------------------------------------------------------------------------


class EnrichmentData(CamelModel):
    personal_number: str | None = None
    name: str | None = None
    enriched_at_utc: datetime | None = None

    spar: SparData | None = None
    company_roles: list[CompanyRolesData] | None = None
    property_ownerships: list[PropertyOwnershipData] | None = None
    income: list[IncomeData] | None = None
    ip_intelligence: IpIntelligenceData | None = None

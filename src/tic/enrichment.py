from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from .data import SigningAuthorityAnalysis
from .models import CamelModel


def _csharp_camel(field_name: str) -> str:
    """Match .NET's ``JsonNamingPolicy.CamelCase`` exactly.

    The TIC API server is .NET. System.Text.Json serialises property
    names by lowercasing the leading run of uppercase letters, but
    keeps the last uppercase before a lowercase letter as-is (the
    standard Pascal-to-camel acronym rule). Examples observed on the
    wire:

    * ``Person_IdNummer`` → ``person_IdNummer`` (single upper, then lower)
    * ``Folkbokforingsadress_SvenskAdress_CareOf`` → ``folkbokforingsadress_SvenskAdress_CareOf``
    * ``AR_DEKL`` → ``ar_DEKL`` (all-upper run followed by underscore)
    * ``INK_NRV_AKT_TOT`` → ``ink_NRV_AKT_TOT``
    * ``XMLDocument`` → ``xmlDocument`` (acronym rule kicks in at ``D``)

    Used for SPAR / Income field aliases — those models keep field
    names matching SPAR / Skatteverket column conventions and don't
    fit pure snake_case ↔ camelCase translation.
    """
    if not field_name or not field_name[0].isupper():
        return field_name

    chars = list(field_name)
    chars[0] = chars[0].lower()

    n = len(chars)
    # If the next char isn't uppercase, we're done (e.g. "Person...").
    if n < 2 or not chars[1].isupper():
        return "".join(chars)

    # Consecutive uppercase letters at the start: lowercase them, but
    # if the next-next char is a lowercase letter, stop one early
    # (acronym rule: XMLDocument → xmlDocument, not xmldocument).
    i = 1
    while i < n and chars[i].isupper():
        if i + 1 < n and chars[i + 1].isalpha() and not chars[i + 1].isupper():
            break
        chars[i] = chars[i].lower()
        i += 1

    return "".join(chars)


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
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=_csharp_camel,
        frozen=True,
    )

    Person_IdNummer: str | None = None
    Person_PersonIdTyp: str | None = None
    Person_SenasteAndringSPAR: str | None = None

    Skydd_Sekretessmarkering: bool | None = None
    Skydd_SkyddadFolkbokforing: bool | None = None
    # The seven `PersonDetaljer_*` fields need explicit aliases — TIC's
    # server-side C# property name is `Persondetaljer_*` (lowercase
    # `d`), even though the public docs show `PersonDetaljer_*`.
    # JsonNamingPolicy.CamelCase therefore emits `persondetaljer_*` on
    # the wire, which doesn't match what `_csharp_camel("PersonDetaljer_*")`
    # would produce (`personDetaljer_*`).
    PersonDetaljer_Sekretessmarkering: bool | None = Field(
        None, alias="persondetaljer_Sekretessmarkering",
    )

    Namn_Fornamn: str | None = None
    Namn_Mellannamn: str | None = None
    Namn_Efternamn: str | None = None
    Namn_Aviseringsnamn: str | None = None
    Namn_Tilltalsnamn: str | None = None

    PersonDetaljer_Kon: str | None = Field(None, alias="persondetaljer_Kon")
    PersonDetaljer_Fodelsedatum: str | None = Field(
        None, alias="persondetaljer_Fodelsedatum",
    )
    PersonDetaljer_Avlidendatum: str | None = Field(
        None, alias="persondetaljer_Avlidendatum",
    )
    PersonDetaljer_Avregistreringsdatum: str | None = Field(
        None, alias="persondetaljer_Avregistreringsdatum",
    )
    PersonDetaljer_AvregistreringsorsakKod: str | None = Field(
        None, alias="persondetaljer_AvregistreringsorsakKod",
    )
    PersonDetaljer_AvregistreringsorsakBeskrivning: str | None = Field(
        None, alias="persondetaljer_AvregistreringsorsakBeskrivning",
    )

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
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=_csharp_camel,
        frozen=True,
    )

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
    domain: str | None = None
    usage_type: str | None = None
    confidence_score: int | None = None
    is_tor: bool = False
    is_likely_vpn: bool = False
    is_whitelisted: bool = False
    total_reports: int | None = None
    distinct_reporters: int | None = None


class IpOverallRisk(CamelModel):
    level: str
    score: int
    indicators: list[str] = []
    requires_review: bool = False


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

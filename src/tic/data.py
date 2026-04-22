from __future__ import annotations

from datetime import datetime


from .models import CamelModel


# ──────────────────────────────────────────────
# Sub-models (alphabetical)
# ──────────────────────────────────────────────


class Address(CamelModel):
    """Registered company address."""

    street_address: str | None = None
    co: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = None  # ISO 3166-1 alpha-3


class BeneficialOwner(CamelModel):
    """Beneficial owner (verklig huvudman)."""

    full_name: str | None = None
    personal_identity_number: str | None = None  # YYYYMMDD-****
    country_of_residence_code: str | None = None
    citizenship_country_code: str | None = None
    extent_code: str | None = None
    extent_description: str | None = None
    govern_description: str | None = None
    through_name: str | None = None
    through_registration_number: str | None = None
    from_date: str | None = None  # ISO 8601


class EligiblePerson(CamelModel):
    """Person eligible to sign on behalf of the company."""

    person_id: int | None = None
    personal_identity_number: str | None = None
    name: str
    roles: list[str]
    can_sign_alone: bool
    applicable_rules: list[str]


class LastStatus(CamelModel):
    """Last registered status from Bolagsverket."""

    status_type: str
    status_date: str | None = None  # ISO 8601
    description: str | None = None


class RegisteredOffice(CamelModel):
    """Registered office (municipality and county)."""

    municipality: str | None = None
    municipality_code: str | None = None
    county: str | None = None
    county_code: str | None = None


class Representative(CamelModel):
    """Board member or signatory representative."""

    full_name: str | None = None
    personal_identity_number: str | None = None  # YYYYMMDD-****
    position_type: str | None = None
    position_description: str | None = None
    position_start: str | None = None  # ISO 8601
    position_end: str | None = None  # ISO 8601, null if ongoing
    role_by_company_name: str | None = None
    role_by_company_registration_number: str | None = None
    employee_representative: bool | None = None
    auditor_type: str | None = (
        None  # CertifiedPublicAccountant | ApprovedAccountant | ForeignAuditor
    )


class SigningRule(CamelModel):
    """A parsed signing authority rule."""

    description: str
    type: str  # alone | joint | board | other
    required_signatories: int | None = None
    required_roles: list[str]


class SniCode(CamelModel):
    """SNI industry classification code."""

    code: str | None = None
    name: str | None = None
    section: str | None = None
    rank: int | None = None  # 1 = primary industry


# ──────────────────────────────────────────────
# Top-level data models
# ──────────────────────────────────────────────


class CompanyLookupData(CamelModel):
    """Company information returned from a company lookup."""

    company_id: int
    registration_number: str
    company_name: str | None = None
    legal_entity_type: str | None = None
    purpose: str | None = None
    registration_date: str | None = None  # ISO 8601
    activity_status: str  # HasNeverBeenActive | IsActive | IsNoLongerActive | Unknown
    last_status: LastStatus | None = None
    registered_address: Address | None = None
    is_registered_for_vat: bool | None = None
    is_registered_for_f_tax: bool | None = None
    is_registered_for_payroll: bool | None = None
    sni_codes_2025: list[SniCode] | None = None
    sni_codes_2007: list[SniCode] | None = None
    employees_category: str | None = None
    turnover_category: str | None = None
    registered_office: RegisteredOffice | None = None
    signatory_description: str | None = None
    representatives: list[Representative] | None = None
    beneficial_owners: list[BeneficialOwner] | None = None


class CompanyCreditData(CamelModel):
    """Credit information for a company."""

    credit_score: int | None = None  # 0-100
    risk_forecast_class: int | None = None  # 1-5 (1 = highest risk)
    risk_forecast: float | None = None  # percentage, e.g. 2.45 = 2.45%


class SigningAuthorityAnalysis(CamelModel):
    """AI-generated analysis of signing authority rules."""

    summary: str
    rules: list[SigningRule]
    eligible_persons: list[EligiblePerson]


# ──────────────────────────────────────────────
# Response wrappers
# ──────────────────────────────────────────────


class ResponseMetadata(CamelModel):
    """Metadata included in every data verification response."""

    requested_at_utc: datetime
    source: str
    country_code: str


class CompanyLookupResponse(CamelModel):
    """Full response envelope for company lookup endpoints."""

    metadata: ResponseMetadata
    data: CompanyLookupData | None = None


class CompanyCreditResponse(CamelModel):
    """Full response envelope for credit information endpoints."""

    metadata: ResponseMetadata
    data: CompanyCreditData | None = None


class SigningAuthorityData(CamelModel):
    """Outer data object for the signing authority analysis endpoint."""

    company_id: int
    registration_number: str
    company_name: str | None = None
    signatory_description: str | None = None
    analysis: SigningAuthorityAnalysis | None = None


class SigningAuthorityResponse(CamelModel):
    """Full response envelope for signing authority analysis endpoints."""

    metadata: ResponseMetadata
    data: SigningAuthorityData | None = None

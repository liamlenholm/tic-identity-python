"""Tests for tic.enrichment — enrichment models, enums, and from_api parsing."""

from __future__ import annotations

from datetime import datetime

from tic.enrichment import (
    EnrichmentData,
    EnrichmentResponse,
    EnrichmentStatus,
    EnrichmentType,
    SparData,
)


# ---------------------------------------------------------------------------
# EnrichmentStatus
# ---------------------------------------------------------------------------


class TestEnrichmentStatus:
    def test_values(self):
        assert EnrichmentStatus.PENDING == "Pending"
        assert EnrichmentStatus.PROCESSING == "Processing"
        assert EnrichmentStatus.COMPLETED == "Completed"
        assert EnrichmentStatus.PARTIALLY_COMPLETED == "PartiallyCompleted"
        assert EnrichmentStatus.FAILED == "Failed"

    def test_member_count(self):
        assert len(EnrichmentStatus) == 5


# ---------------------------------------------------------------------------
# EnrichmentType
# ---------------------------------------------------------------------------


class TestEnrichmentType:
    def test_values(self):
        assert EnrichmentType.SPAR == "SPAR"
        assert EnrichmentType.COMPANY_ROLES == "CompanyRoles"
        assert EnrichmentType.PROPERTY_OWNERSHIP == "PropertyOwnership"
        assert EnrichmentType.INCOME == "Income"
        assert EnrichmentType.IP_INTELLIGENCE == "IpIntelligence"
        assert EnrichmentType.FULL == "Full"

    def test_member_count(self):
        assert len(EnrichmentType) == 6


# ---------------------------------------------------------------------------
# EnrichmentResponse
# ---------------------------------------------------------------------------


class TestEnrichmentResponse:
    def test_from_api_minimal(self):
        data = {
            "enrichmentId": "enr-001",
            "sessionId": "sess-001",
            "status": "Pending",
            "requestedTypes": ["SPAR", "CompanyRoles"],
            "completedTypes": [],
        }
        resp = EnrichmentResponse.from_api(data)
        assert resp.enrichment_id == "enr-001"
        assert resp.session_id == "sess-001"
        assert resp.status == EnrichmentStatus.PENDING
        assert resp.requested_types == ["SPAR", "CompanyRoles"]
        assert resp.completed_types == []
        assert resp.secure_url is None
        assert resp.secure_url_expires_at_utc is None

    def test_from_api_completed_with_url(self):
        data = {
            "enrichmentId": "enr-002",
            "sessionId": "sess-002",
            "status": "Completed",
            "requestedTypes": ["SPAR"],
            "completedTypes": ["SPAR"],
            "secureUrl": "https://id.tic.io/api/v1/enrichment/data/token-xyz",
            "secureUrlExpiresAtUtc": "2026-06-15T12:30:00Z",
        }
        resp = EnrichmentResponse.from_api(data)
        assert resp.status == EnrichmentStatus.COMPLETED
        assert resp.secure_url == "https://id.tic.io/api/v1/enrichment/data/token-xyz"
        assert isinstance(resp.secure_url_expires_at_utc, datetime)
        assert resp.completed_types == ["SPAR"]

    def test_from_api_partially_completed(self):
        data = {
            "enrichmentId": "enr-003",
            "sessionId": "sess-003",
            "status": "PartiallyCompleted",
            "requestedTypes": ["SPAR", "Income"],
            "completedTypes": ["SPAR"],
            "secureUrl": "https://id.tic.io/api/v1/enrichment/data/token-abc",
            "secureUrlExpiresAtUtc": "2026-06-15T13:00:00Z",
        }
        resp = EnrichmentResponse.from_api(data)
        assert resp.status == EnrichmentStatus.PARTIALLY_COMPLETED
        assert len(resp.completed_types) == 1

    def test_to_api_round_trip(self):
        data = {
            "enrichmentId": "enr-004",
            "sessionId": "sess-004",
            "status": "Pending",
            "requestedTypes": ["SPAR"],
            "completedTypes": [],
        }
        resp = EnrichmentResponse.from_api(data)
        dumped = resp.to_api()
        assert dumped["enrichmentId"] == "enr-004"
        assert dumped["sessionId"] == "sess-004"
        assert dumped["status"] == "Pending"


# ---------------------------------------------------------------------------
# EnrichmentData — full payload
# ---------------------------------------------------------------------------


class TestEnrichmentData:
    def test_from_api_with_spar(self):
        data = {
            "personalNumber": "199001011234",
            "name": "Anna Svensson",
            "enrichedAtUtc": "2026-06-15T12:00:00Z",
            "spar": {
                "Person_IdNummer": "199001011234",
                "Person_PersonIdTyp": "PersonNummer",
                "Namn_Fornamn": "Anna",
                "Namn_Efternamn": "Svensson",
                "Skydd_Sekretessmarkering": False,
                "Folkbokforingsadress_SvenskAdress_PostNr": "11122",
                "Folkbokforingsadress_SvenskAdress_Postort": "Stockholm",
            },
        }
        enrichment = EnrichmentData.from_api(data)
        assert enrichment.personal_number == "199001011234"
        assert enrichment.name == "Anna Svensson"
        assert isinstance(enrichment.enriched_at_utc, datetime)
        assert enrichment.spar is not None
        assert enrichment.spar.Person_IdNummer == "199001011234"
        assert enrichment.spar.Namn_Fornamn == "Anna"
        assert enrichment.spar.Namn_Efternamn == "Svensson"
        assert enrichment.spar.Skydd_Sekretessmarkering is False
        assert enrichment.spar.Folkbokforingsadress_SvenskAdress_PostNr == "11122"

    def test_from_api_with_company_roles(self):
        data = {
            "personalNumber": "199001011234",
            "name": "Erik Johansson",
            "companyRoles": [
                {
                    "companyId": 12345,
                    "companyRegistrationNumber": "5591234567",
                    "legalName": "Exempelbolaget AB",
                    "legalEntityType": "AB",
                    "positionTypes": ["BoardMember", "CEO"],
                    "positionDescriptions": [
                        "Styrelseledamot",
                        "Verkstallande direktor",
                    ],
                    "positionStart": "2020-01-15",
                    "companyStatus": "Active",
                    "signatureDescription": "Firman tecknas av styrelsens ledamoter var for sig.",
                    "signingAuthorityAnalysis": {
                        "summary": "Each board member can sign alone.",
                        "rules": [
                            {
                                "description": "Board members sign individually",
                                "type": "alone",
                                "requiredSignatories": 1,
                                "requiredRoles": ["BoardMember"],
                            }
                        ],
                        "eligiblePersons": [
                            {
                                "personId": 100,
                                "personalIdentityNumber": "199001011234",
                                "name": "Erik Johansson",
                                "roles": ["BoardMember", "CEO"],
                                "canSignAlone": True,
                                "applicableRules": ["Board members sign individually"],
                            }
                        ],
                    },
                }
            ],
        }
        enrichment = EnrichmentData.from_api(data)
        assert enrichment.company_roles is not None
        assert len(enrichment.company_roles) == 1
        role = enrichment.company_roles[0]
        assert role.company_id == 12345
        assert role.company_registration_number == "5591234567"
        assert role.legal_name == "Exempelbolaget AB"
        assert role.position_types == ["BoardMember", "CEO"]
        assert role.signing_authority_analysis is not None
        analysis = role.signing_authority_analysis
        assert len(analysis.rules) == 1
        assert analysis.rules[0].required_signatories == 1
        assert len(analysis.eligible_persons) == 1
        assert analysis.eligible_persons[0].can_sign_alone is True

    def test_from_api_minimal(self):
        data = {
            "personalNumber": "200101011234",
        }
        enrichment = EnrichmentData.from_api(data)
        assert enrichment.personal_number == "200101011234"
        assert enrichment.name is None
        assert enrichment.spar is None
        assert enrichment.company_roles is None
        assert enrichment.property_ownerships is None
        assert enrichment.income is None
        assert enrichment.ip_intelligence is None

    def test_from_api_with_ip_intelligence(self):
        data = {
            "personalNumber": "199001011234",
            "ipIntelligence": {
                "initiatingIp": {
                    "ipAddress": "203.0.113.42",
                    "countryCode": "SE",
                    "countryName": "Sweden",
                    "isp": "Telia",
                    "isTor": False,
                    "isLikelyVpn": False,
                },
                "overallRisk": {
                    "level": "low",
                    "score": 10,
                    "indicators": [],
                },
                "enrichedAtUtc": "2026-06-15T12:00:00Z",
            },
        }
        enrichment = EnrichmentData.from_api(data)
        assert enrichment.ip_intelligence is not None
        ip = enrichment.ip_intelligence
        assert ip.initiating_ip is not None
        assert ip.initiating_ip.ip_address == "203.0.113.42"
        assert ip.initiating_ip.country_code == "SE"
        assert ip.overall_risk is not None
        assert ip.overall_risk.level == "low"
        assert ip.overall_risk.score == 10


# ---------------------------------------------------------------------------
# SparData
# ---------------------------------------------------------------------------


class TestSparData:
    def test_from_dict_with_aliases(self):
        data = {
            "Person_IdNummer": "199505051234",
            "Namn_Fornamn": "Lisa",
            "Namn_Efternamn": "Karlsson",
            "Skydd_Sekretessmarkering": True,
        }
        spar = SparData.model_validate(data)
        assert spar.Person_IdNummer == "199505051234"
        assert spar.Namn_Fornamn == "Lisa"
        assert spar.Skydd_Sekretessmarkering is True

    def test_all_fields_default_to_none(self):
        spar = SparData.model_validate({})
        assert spar.Person_IdNummer is None
        assert spar.Namn_Fornamn is None
        assert spar.Namn_Efternamn is None
        assert spar.Folkbokforingsadress_SvenskAdress_PostNr is None

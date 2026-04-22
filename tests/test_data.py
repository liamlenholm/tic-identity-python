"""Tests for tic.data — company lookup, credit, and signing authority models."""

from __future__ import annotations

from datetime import datetime

from tic.data import (
    Address,
    CompanyCreditResponse,
    CompanyLookupResponse,
    Representative,
    ResponseMetadata,
    SigningAuthorityResponse,
    SniCode,
)


# ---------------------------------------------------------------------------
# CompanyLookupResponse
# ---------------------------------------------------------------------------


class TestCompanyLookupResponse:
    def test_from_api_full(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "Bolagsverket",
                "countryCode": "SE",
            },
            "data": {
                "companyId": 98765,
                "registrationNumber": "5591234567",
                "companyName": "Exempelbolaget AB",
                "legalEntityType": "AB",
                "purpose": "Software development and consulting",
                "registrationDate": "2015-03-20",
                "activityStatus": "IsActive",
                "lastStatus": {
                    "statusType": "Active",
                    "statusDate": "2026-01-01",
                    "description": "Registered and active",
                },
                "registeredAddress": {
                    "streetAddress": "Kungsgatan 10",
                    "postalCode": "11143",
                    "city": "Stockholm",
                    "countryCode": "SWE",
                },
                "isRegisteredForVat": True,
                "isRegisteredForFTax": True,
                "isRegisteredForPayroll": True,
                "sniCodes2025": [
                    {
                        "code": "62010",
                        "name": "Computer programming activities",
                        "section": "J",
                        "rank": 1,
                    },
                ],
                "employeesCategory": "10-19",
                "turnoverCategory": "10-50 MSEK",
                "registeredOffice": {
                    "municipality": "Stockholm",
                    "municipalityCode": "0180",
                    "county": "Stockholms lan",
                    "countyCode": "01",
                },
                "signatoryDescription": "Firman tecknas av styrelsens ledamoter var for sig.",
                "representatives": [
                    {
                        "fullName": "Anna Svensson",
                        "personalIdentityNumber": "199001****",
                        "positionType": "BoardMember",
                        "positionDescription": "Styrelseledamot",
                        "positionStart": "2020-01-15",
                    },
                    {
                        "fullName": "Erik Johansson",
                        "personalIdentityNumber": "198505****",
                        "positionType": "CEO",
                        "positionDescription": "Verkstallande direktor",
                        "positionStart": "2020-03-01",
                    },
                ],
                "beneficialOwners": [
                    {
                        "fullName": "Anna Svensson",
                        "personalIdentityNumber": "19900101****",
                        "countryOfResidenceCode": "SE",
                        "citizenshipCountryCode": "SE",
                        "extentCode": "25-50",
                        "extentDescription": "25-50% of votes",
                        "fromDate": "2015-03-20",
                    },
                ],
            },
        }
        resp = CompanyLookupResponse.from_api(data)

        # Metadata
        assert isinstance(resp.metadata.requested_at_utc, datetime)
        assert resp.metadata.source == "Bolagsverket"
        assert resp.metadata.country_code == "SE"

        # Company data
        assert resp.data is not None
        company = resp.data
        assert company.company_id == 98765
        assert company.registration_number == "5591234567"
        assert company.company_name == "Exempelbolaget AB"
        assert company.legal_entity_type == "AB"
        assert company.activity_status == "IsActive"
        assert company.is_registered_for_vat is True
        assert company.is_registered_for_f_tax is True

        # LastStatus
        assert company.last_status is not None
        assert company.last_status.status_type == "Active"

        # Address
        assert company.registered_address is not None
        assert company.registered_address.street_address == "Kungsgatan 10"
        assert company.registered_address.postal_code == "11143"
        assert company.registered_address.city == "Stockholm"

        # SNI codes
        assert company.sni_codes_2025 is not None
        assert len(company.sni_codes_2025) == 1
        assert company.sni_codes_2025[0].code == "62010"
        assert company.sni_codes_2025[0].rank == 1

        # Registered office
        assert company.registered_office is not None
        assert company.registered_office.municipality == "Stockholm"

        # Representatives
        assert company.representatives is not None
        assert len(company.representatives) == 2
        assert company.representatives[0].full_name == "Anna Svensson"
        assert company.representatives[0].position_type == "BoardMember"
        assert company.representatives[1].position_type == "CEO"

        # Beneficial owners
        assert company.beneficial_owners is not None
        assert len(company.beneficial_owners) == 1
        assert company.beneficial_owners[0].full_name == "Anna Svensson"
        assert company.beneficial_owners[0].extent_code == "25-50"

    def test_from_api_minimal(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "Bolagsverket",
                "countryCode": "SE",
            },
            "data": {
                "companyId": 11111,
                "registrationNumber": "5590000001",
                "activityStatus": "HasNeverBeenActive",
            },
        }
        resp = CompanyLookupResponse.from_api(data)
        assert resp.data is not None
        assert resp.data.company_name is None
        assert resp.data.representatives is None
        assert resp.data.beneficial_owners is None
        assert resp.data.registered_address is None
        assert resp.data.sni_codes_2025 is None

    def test_from_api_data_none(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "Bolagsverket",
                "countryCode": "SE",
            },
        }
        resp = CompanyLookupResponse.from_api(data)
        assert resp.data is None

    def test_to_api_produces_camel_case(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "Bolagsverket",
                "countryCode": "SE",
            },
            "data": {
                "companyId": 22222,
                "registrationNumber": "5590000002",
                "activityStatus": "IsActive",
                "isRegisteredForVat": True,
            },
        }
        resp = CompanyLookupResponse.from_api(data)
        dumped = resp.to_api()
        assert "companyId" in dumped["data"]
        assert "registrationNumber" in dumped["data"]
        assert "requestedAtUtc" in dumped["metadata"]


# ---------------------------------------------------------------------------
# CompanyCreditResponse
# ---------------------------------------------------------------------------


class TestCompanyCreditResponse:
    def test_from_api_full(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "CreditProvider",
                "countryCode": "SE",
            },
            "data": {
                "creditScore": 85,
                "riskForecastClass": 4,
                "riskForecast": 1.25,
            },
        }
        resp = CompanyCreditResponse.from_api(data)
        assert resp.metadata.source == "CreditProvider"
        assert resp.data is not None
        assert resp.data.credit_score == 85
        assert resp.data.risk_forecast_class == 4
        assert resp.data.risk_forecast == 1.25

    def test_from_api_data_none(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "CreditProvider",
                "countryCode": "SE",
            },
        }
        resp = CompanyCreditResponse.from_api(data)
        assert resp.data is None

    def test_from_api_partial_credit_data(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "CreditProvider",
                "countryCode": "SE",
            },
            "data": {
                "creditScore": 50,
            },
        }
        resp = CompanyCreditResponse.from_api(data)
        assert resp.data is not None
        assert resp.data.credit_score == 50
        assert resp.data.risk_forecast_class is None
        assert resp.data.risk_forecast is None

    def test_to_api_round_trip(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "CreditProvider",
                "countryCode": "SE",
            },
            "data": {
                "creditScore": 72,
                "riskForecastClass": 3,
                "riskForecast": 2.45,
            },
        }
        resp = CompanyCreditResponse.from_api(data)
        dumped = resp.to_api()
        assert dumped["data"]["creditScore"] == 72
        assert dumped["data"]["riskForecastClass"] == 3


# ---------------------------------------------------------------------------
# SigningAuthorityResponse
# ---------------------------------------------------------------------------


class TestSigningAuthorityResponse:
    def test_from_api_with_rules_and_persons(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "Bolagsverket",
                "countryCode": "SE",
            },
            "data": {
                "companyId": 98765,
                "registrationNumber": "5591234567",
                "companyName": "Exempelbolaget AB",
                "signatoryDescription": "Firman tecknas av styrelsens ledamoter var for sig.",
                "analysis": {
                    "summary": "Each board member can sign alone. The CEO can also sign alone.",
                    "rules": [
                        {
                            "description": "Board members sign individually",
                            "type": "alone",
                            "requiredSignatories": 1,
                            "requiredRoles": ["BoardMember"],
                        },
                        {
                            "description": "Two board members sign jointly",
                            "type": "joint",
                            "requiredSignatories": 2,
                            "requiredRoles": ["BoardMember"],
                        },
                    ],
                    "eligiblePersons": [
                        {
                            "personalIdentityNumber": "199001011234",
                            "name": "Anna Svensson",
                            "roles": ["BoardMember", "Chairman"],
                            "canSignAlone": True,
                            "applicableRules": ["Board members sign individually"],
                        },
                        {
                            "personalIdentityNumber": "198505051234",
                            "name": "Erik Johansson",
                            "roles": ["CEO"],
                            "canSignAlone": True,
                            "applicableRules": ["Board members sign individually"],
                        },
                    ],
                },
            },
        }
        resp = SigningAuthorityResponse.from_api(data)
        assert resp.metadata.source == "Bolagsverket"
        assert resp.data is not None
        assert resp.data.company_id == 98765
        assert resp.data.registration_number == "5591234567"
        assert resp.data.company_name == "Exempelbolaget AB"
        assert resp.data.signatory_description is not None

        analysis = resp.data.analysis
        assert analysis is not None
        assert "board member" in analysis.summary.lower()

        # Rules
        assert len(analysis.rules) == 2
        assert analysis.rules[0].type == "alone"
        assert analysis.rules[0].required_signatories == 1
        assert analysis.rules[0].required_roles == ["BoardMember"]
        assert analysis.rules[1].type == "joint"
        assert analysis.rules[1].required_signatories == 2

        # Eligible persons
        assert len(analysis.eligible_persons) == 2
        assert analysis.eligible_persons[0].name == "Anna Svensson"
        assert analysis.eligible_persons[0].can_sign_alone is True
        assert "BoardMember" in analysis.eligible_persons[0].roles
        assert analysis.eligible_persons[1].name == "Erik Johansson"

    def test_from_api_without_analysis(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "Bolagsverket",
                "countryCode": "SE",
            },
            "data": {
                "companyId": 11111,
                "registrationNumber": "5590000001",
                "signatoryDescription": "Styrelsen tecknar firman.",
            },
        }
        resp = SigningAuthorityResponse.from_api(data)
        assert resp.data is not None
        assert resp.data.analysis is None
        assert resp.data.company_name is None

    def test_from_api_data_none(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "Bolagsverket",
                "countryCode": "SE",
            },
        }
        resp = SigningAuthorityResponse.from_api(data)
        assert resp.data is None

    def test_to_api_camel_case_keys(self):
        data = {
            "metadata": {
                "requestedAtUtc": "2026-06-15T10:00:00Z",
                "source": "Bolagsverket",
                "countryCode": "SE",
            },
            "data": {
                "companyId": 98765,
                "registrationNumber": "5591234567",
                "companyName": "Test AB",
                "signatoryDescription": "Test",
                "analysis": {
                    "summary": "Test summary",
                    "rules": [],
                    "eligiblePersons": [],
                },
            },
        }
        resp = SigningAuthorityResponse.from_api(data)
        dumped = resp.to_api()
        assert "companyId" in dumped["data"]
        assert "registrationNumber" in dumped["data"]
        assert "signatoryDescription" in dumped["data"]


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class TestResponseMetadata:
    def test_from_api(self):
        data = {
            "requestedAtUtc": "2026-06-15T10:00:00Z",
            "source": "Bolagsverket",
            "countryCode": "SE",
        }
        meta = ResponseMetadata.from_api(data)
        assert isinstance(meta.requested_at_utc, datetime)
        assert meta.source == "Bolagsverket"
        assert meta.country_code == "SE"


class TestAddress:
    def test_from_api(self):
        data = {
            "streetAddress": "Storgatan 1",
            "co": "c/o Fastigheten",
            "postalCode": "11122",
            "city": "Stockholm",
            "countryCode": "SWE",
        }
        addr = Address.from_api(data)
        assert addr.street_address == "Storgatan 1"
        assert addr.co == "c/o Fastigheten"
        assert addr.postal_code == "11122"

    def test_all_fields_optional(self):
        addr = Address.from_api({})
        assert addr.street_address is None
        assert addr.city is None


class TestSniCode:
    def test_from_api(self):
        data = {"code": "62010", "name": "Programming", "section": "J", "rank": 1}
        sni = SniCode.from_api(data)
        assert sni.code == "62010"
        assert sni.rank == 1


class TestRepresentative:
    def test_from_api(self):
        data = {
            "fullName": "Anna Svensson",
            "personalIdentityNumber": "199001****",
            "positionType": "BoardMember",
            "positionDescription": "Styrelseledamot",
            "positionStart": "2020-01-15",
            "employeeRepresentative": False,
        }
        rep = Representative.from_api(data)
        assert rep.full_name == "Anna Svensson"
        assert rep.position_type == "BoardMember"
        assert rep.employee_representative is False
        assert rep.position_end is None

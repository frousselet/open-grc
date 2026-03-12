import pytest
from django.urls import reverse
from django.utils import timezone

from compliance.constants import ComplianceStatus
from compliance.models.assessment import AssessmentResult
from compliance.tests.factories import (
    AssessmentResultFactory,
    ComplianceAssessmentFactory,
    FrameworkFactory,
    RequirementFactory,
    SectionFactory,
)

pytestmark = pytest.mark.django_db


class TestInitializeResults:
    def test_initialize_creates_results_for_all_applicable_requirements(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="u@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        req2 = RequirementFactory(framework=fw, is_applicable=True)
        RequirementFactory(framework=fw, is_applicable=False)  # not applicable
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)

        url = reverse("compliance:assessment-initialize-results", args=[assessment.pk])
        response = client.post(url)

        assert response.status_code == 302
        assert assessment.results.count() == 2
        assert set(assessment.results.values_list("requirement_id", flat=True)) == {req1.pk, req2.pk}
        for result in assessment.results.all():
            assert result.compliance_status == ComplianceStatus.NOT_ASSESSED
            assert result.compliance_level == 0

    def test_initialize_is_idempotent(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="u2@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)

        url = reverse("compliance:assessment-initialize-results", args=[assessment.pk])
        client.post(url)
        client.post(url)

        assert assessment.results.count() == 1

    def test_initialize_via_htmx_returns_204(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="u3@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)

        url = reverse("compliance:assessment-initialize-results", args=[assessment.pk])
        response = client.post(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 204
        assert response["HX-Trigger"] == "formSaved"


class TestAssessmentResultCreateView:
    def test_create_result_via_drawer(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="c@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)

        create_url = reverse("compliance:assessment-result-create", args=[assessment.pk])

        # GET returns modal form
        response = client.get(create_url + f"?requirement={req.pk}", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        assert b"clipboard-check" in response.content

        # POST creates the result
        response = client.post(
            create_url + f"?requirement={req.pk}",
            {
                "requirement": str(req.pk),
                "compliance_status": ComplianceStatus.COMPLIANT,
                "compliance_level": 100,
                "evidence": "All controls implemented",
                "finding": "",
                "auditor_recommendations": "",
            },
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 204
        assert assessment.results.count() == 1
        result = assessment.results.first()
        assert result.compliance_status == ComplianceStatus.COMPLIANT
        assert result.compliance_level == 100
        assert result.assessed_by == user


class TestAssessmentResultUpdateView:
    def test_update_result(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="e@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)
        result = AssessmentResultFactory(
            assessment=assessment,
            requirement=req,
            compliance_status=ComplianceStatus.NOT_ASSESSED,
            compliance_level=0,
            assessed_by=user,
        )

        url = reverse(
            "compliance:assessment-result-update",
            args=[assessment.pk, result.pk],
        )
        response = client.post(
            url,
            {
                "requirement": str(req.pk),
                "compliance_status": ComplianceStatus.MINOR_NON_CONFORMITY,
                "compliance_level": 30,
                "evidence": "Partial",
                "finding": "Missing controls",
                "auditor_recommendations": "",
            },
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 204
        result.refresh_from_db()
        assert result.compliance_status == ComplianceStatus.MINOR_NON_CONFORMITY
        assert result.compliance_level == 30


class TestAssessmentResultDeleteView:
    def test_delete_result_recalculates_counts(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="d@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)
        result = AssessmentResultFactory(
            assessment=assessment,
            requirement=req,
            compliance_status=ComplianceStatus.COMPLIANT,
            compliance_level=100,
            assessed_by=user,
        )
        assessment.recalculate_counts()
        assessment.refresh_from_db()
        assert assessment.compliant_count == 1

        url = reverse(
            "compliance:assessment-result-delete",
            args=[assessment.pk, result.pk],
        )
        response = client.post(url)
        assert response.status_code == 302
        assert assessment.results.count() == 0
        assessment.refresh_from_db()
        assert assessment.compliant_count == 0


class TestAssessmentResultsTableBody:
    def test_table_body_grouped_by_section(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="tb@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        sec1 = SectionFactory(framework=fw, name="Section A", order=1)
        sec2 = SectionFactory(framework=fw, name="Section B", order=2)
        RequirementFactory(framework=fw, section=sec1, is_applicable=True, name="Req A1")
        RequirementFactory(framework=fw, section=sec2, is_applicable=True, name="Req B1")
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)

        # Initialize results
        init_url = reverse("compliance:assessment-initialize-results", args=[assessment.pk])
        client.post(init_url)

        url = reverse("compliance:assessment-results-table-body", args=[assessment.pk])
        response = client.get(url)
        content = response.content.decode()
        assert "Section A" in content
        assert "Section B" in content
        assert "Req A1" in content
        assert "Req B1" in content


class TestRecalculateCounts:
    def test_counts_updated_after_result_changes(self, django_user_model):
        user = django_user_model.objects.create_user(email="rc@t.com", password="pw")
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        req2 = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)

        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.COMPLIANT, compliance_level=100,
            assessed_by=user,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req2,
            compliance_status=ComplianceStatus.MAJOR_NON_CONFORMITY, compliance_level=0,
            assessed_by=user,
        )
        assessment.recalculate_counts()
        assessment.refresh_from_db()

        assert assessment.total_requirements == 2
        assert assessment.compliant_count == 1
        assert assessment.major_non_conformity_count == 1
        assert assessment.overall_compliance_level == 50


class TestAssessmentDetailView:
    def test_detail_shows_results_tab(self, client, django_user_model):
        user = django_user_model.objects.create_superuser(email="det@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)

        url = reverse("compliance:assessment-detail", args=[assessment.pk])
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "results_tab" in content
        assert "Initialize evaluations" in content or "Initialiser" in content

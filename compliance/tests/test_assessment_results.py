import pytest
from django.urls import reverse
from django.utils import timezone

from compliance.constants import AssessmentStatus, ComplianceStatus
from compliance.models.assessment import AssessmentResult
from compliance.tests.factories import (
    AssessmentResultFactory,
    ComplianceAssessmentFactory,
    FrameworkFactory,
    RequirementFactory,
    SectionFactory,
)

pytestmark = pytest.mark.django_db


# ── Toggle (single requirement) ─────────────────────────────

class TestToggleDraftPlanned:
    """In DRAFT / PLANNED: toggle cycles NOT_ASSESSED ↔ EVALUATED."""

    @pytest.fixture
    def setup(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="td@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.DRAFT,
        )
        result = AssessmentResultFactory(
            assessment=assessment, requirement=req,
            compliance_status=ComplianceStatus.NOT_ASSESSED, compliance_level=0,
            assessed_by=user,
        )
        url = reverse("compliance:assessment-result-toggle", args=[assessment.pk, req.pk])
        return {"client": client, "url": url, "result": result, "assessment": assessment, "req": req}

    def test_draft_not_assessed_to_evaluated(self, setup):
        response = setup["client"].post(setup["url"])
        assert response.status_code == 204
        setup["result"].refresh_from_db()
        assert setup["result"].compliance_status == ComplianceStatus.EVALUATED
        assert setup["result"].compliance_level == 50

    def test_draft_evaluated_to_not_assessed(self, setup):
        # First toggle to EVALUATED
        setup["client"].post(setup["url"])
        # Second toggle back to NOT_ASSESSED
        response = setup["client"].post(setup["url"])
        assert response.status_code == 204
        setup["result"].refresh_from_db()
        assert setup["result"].compliance_status == ComplianceStatus.NOT_ASSESSED
        assert setup["result"].compliance_level == 0

    def test_planned_same_behaviour(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="tp@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.PLANNED,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req,
            compliance_status=ComplianceStatus.NOT_ASSESSED, compliance_level=0,
            assessed_by=user,
        )
        url = reverse("compliance:assessment-result-toggle", args=[assessment.pk, req.pk])
        response = client.post(url)
        assert response.status_code == 204
        r = assessment.results.get(requirement=req)
        assert r.compliance_status == ComplianceStatus.EVALUATED

    def test_draft_creates_result_as_evaluated(self, client, django_user_model):
        """When no result exists yet in DRAFT, get_or_create defaults to EVALUATED."""
        user = django_user_model.objects.create_user(email="tc@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.DRAFT,
        )
        url = reverse("compliance:assessment-result-toggle", args=[assessment.pk, req.pk])
        response = client.post(url)
        assert response.status_code == 204
        r = assessment.results.get(requirement=req)
        assert r.compliance_status == ComplianceStatus.EVALUATED
        assert r.compliance_level == 50


class TestToggleInProgress:
    """In IN_PROGRESS: toggle cycles EVALUATED ↔ COMPLIANT; NOT_ASSESSED frozen."""

    def test_evaluated_to_compliant(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="tip1@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req,
            compliance_status=ComplianceStatus.EVALUATED, compliance_level=50,
            assessed_by=user,
        )
        url = reverse("compliance:assessment-result-toggle", args=[assessment.pk, req.pk])
        response = client.post(url)
        assert response.status_code == 204
        r = assessment.results.get(requirement=req)
        assert r.compliance_status == ComplianceStatus.COMPLIANT
        assert r.compliance_level == 100

    def test_compliant_to_evaluated(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="tip2@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req,
            compliance_status=ComplianceStatus.COMPLIANT, compliance_level=100,
            assessed_by=user,
        )
        url = reverse("compliance:assessment-result-toggle", args=[assessment.pk, req.pk])
        response = client.post(url)
        assert response.status_code == 204
        r = assessment.results.get(requirement=req)
        assert r.compliance_status == ComplianceStatus.EVALUATED
        assert r.compliance_level == 50

    def test_not_assessed_frozen_returns_409(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="tip3@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req,
            compliance_status=ComplianceStatus.NOT_ASSESSED, compliance_level=0,
            assessed_by=user,
        )
        url = reverse("compliance:assessment-result-toggle", args=[assessment.pk, req.pk])
        response = client.post(url)
        assert response.status_code == 409

    def test_creates_result_as_compliant(self, client, django_user_model):
        """When no result exists in IN_PROGRESS, get_or_create defaults to COMPLIANT."""
        user = django_user_model.objects.create_user(email="tip4@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS,
        )
        url = reverse("compliance:assessment-result-toggle", args=[assessment.pk, req.pk])
        response = client.post(url)
        assert response.status_code == 204
        r = assessment.results.get(requirement=req)
        assert r.compliance_status == ComplianceStatus.COMPLIANT
        assert r.compliance_level == 100


class TestToggleCompleted:
    """In COMPLETED / CLOSED: toggle returns 403."""

    def test_completed_returns_403(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="tc403@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.COMPLETED,
        )
        url = reverse("compliance:assessment-result-toggle", args=[assessment.pk, req.pk])
        response = client.post(url)
        assert response.status_code == 403


# ── Bulk toggle ──────────────────────────────────────────────

class TestBulkToggleDraftPlanned:
    """In DRAFT/PLANNED: bulk toggles NOT_ASSESSED ↔ EVALUATED."""

    def test_bulk_selects_all_not_assessed_to_evaluated(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="bt1@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        req2 = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.DRAFT,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.NOT_ASSESSED, compliance_level=0,
            assessed_by=user,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req2,
            compliance_status=ComplianceStatus.NOT_ASSESSED, compliance_level=0,
            assessed_by=user,
        )

        url = reverse("compliance:assessment-bulk-toggle-evaluated", args=[assessment.pk])
        response = client.post(url)
        assert response.status_code == 204

        r1 = assessment.results.get(requirement=req1)
        r2 = assessment.results.get(requirement=req2)
        assert r1.compliance_status == ComplianceStatus.EVALUATED
        assert r2.compliance_status == ComplianceStatus.EVALUATED

    def test_bulk_deselects_all_evaluated_to_not_assessed(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="bt2@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.PLANNED,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.EVALUATED, compliance_level=50,
            assessed_by=user,
        )

        url = reverse("compliance:assessment-bulk-toggle-evaluated", args=[assessment.pk])
        response = client.post(url)
        assert response.status_code == 204

        r1 = assessment.results.get(requirement=req1)
        assert r1.compliance_status == ComplianceStatus.NOT_ASSESSED


class TestBulkToggleInProgress:
    """In IN_PROGRESS: bulk toggles EVALUATED ↔ COMPLIANT."""

    def test_bulk_evaluated_to_compliant(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="bip1@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        req2 = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.EVALUATED, compliance_level=50,
            assessed_by=user,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req2,
            compliance_status=ComplianceStatus.EVALUATED, compliance_level=50,
            assessed_by=user,
        )

        url = reverse("compliance:assessment-bulk-toggle-evaluated", args=[assessment.pk])
        response = client.post(url)
        assert response.status_code == 204

        r1 = assessment.results.get(requirement=req1)
        r2 = assessment.results.get(requirement=req2)
        assert r1.compliance_status == ComplianceStatus.COMPLIANT
        assert r2.compliance_status == ComplianceStatus.COMPLIANT

    def test_bulk_compliant_to_evaluated(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="bip2@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.COMPLIANT, compliance_level=100,
            assessed_by=user,
        )

        url = reverse("compliance:assessment-bulk-toggle-evaluated", args=[assessment.pk])
        response = client.post(url)
        assert response.status_code == 204

        r1 = assessment.results.get(requirement=req1)
        assert r1.compliance_status == ComplianceStatus.EVALUATED

    def test_bulk_skips_not_assessed_in_progress(self, client, django_user_model):
        """NOT_ASSESSED results are not touched when bulk toggling in IN_PROGRESS."""
        user = django_user_model.objects.create_user(email="bip3@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req_eval = RequirementFactory(framework=fw, is_applicable=True)
        req_na = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req_eval,
            compliance_status=ComplianceStatus.EVALUATED, compliance_level=50,
            assessed_by=user,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req_na,
            compliance_status=ComplianceStatus.NOT_ASSESSED, compliance_level=0,
            assessed_by=user,
        )

        url = reverse("compliance:assessment-bulk-toggle-evaluated", args=[assessment.pk])
        response = client.post(url)
        assert response.status_code == 204

        r_eval = assessment.results.get(requirement=req_eval)
        r_na = assessment.results.get(requirement=req_na)
        assert r_eval.compliance_status == ComplianceStatus.COMPLIANT
        assert r_na.compliance_status == ComplianceStatus.NOT_ASSESSED  # untouched


# ── CRUD & other existing tests ──────────────────────────────

class TestAssessmentResultCreateView:
    def test_create_result_via_drawer(self, client, django_user_model):
        user = django_user_model.objects.create_user(email="c@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS)

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
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS)
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
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS)
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
        req1 = RequirementFactory(framework=fw, section=sec1, is_applicable=True, name="Req A1")
        req2 = RequirementFactory(framework=fw, section=sec2, is_applicable=True, name="Req B1")
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user, status=AssessmentStatus.DRAFT)

        # Create results via bulk toggle (creates missing results automatically)
        bulk_url = reverse("compliance:assessment-bulk-toggle-evaluated", args=[assessment.pk])
        client.post(bulk_url)

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


class TestNonApplicableRequirements:
    def test_toggle_blocked_for_non_applicable(self, client, django_user_model):
        """Non-applicable requirements cannot be toggled."""
        user = django_user_model.objects.create_user(email="na1@t.com", password="pw")
        client.force_login(user)
        fw = FrameworkFactory()
        req_na = RequirementFactory(framework=fw, is_applicable=False)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user, status=AssessmentStatus.IN_PROGRESS)
        AssessmentResultFactory(
            assessment=assessment, requirement=req_na,
            compliance_status=ComplianceStatus.NOT_APPLICABLE,
            compliance_level=100, assessed_by=user,
        )

        url = reverse("compliance:assessment-result-toggle",
                       args=[assessment.pk, req_na.pk])
        response = client.post(url)
        assert response.status_code == 409

    def test_findings_dont_change_non_applicable_status(self, django_user_model):
        """Findings linked to non-applicable requirements don't change their status."""
        from compliance.tests.factories import FindingFactory
        from compliance.constants import FindingType

        user = django_user_model.objects.create_user(email="na2@t.com", password="pw")
        fw = FrameworkFactory()
        req_na = RequirementFactory(framework=fw, is_applicable=False)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)
        result = AssessmentResultFactory(
            assessment=assessment, requirement=req_na,
            compliance_status=ComplianceStatus.NOT_APPLICABLE,
            compliance_level=100, assessed_by=user,
        )

        finding = FindingFactory(
            assessment=assessment,
            finding_type=FindingType.MAJOR_NON_CONFORMITY,
            assessor=user,
        )
        finding.requirements.add(req_na)

        assessment.apply_findings_to_results()
        result.refresh_from_db()
        assert result.compliance_status == ComplianceStatus.NOT_APPLICABLE
        assert result.compliance_level == 100

    def test_recalculate_counts_includes_not_applicable(self, django_user_model):
        """recalculate_counts correctly counts not_applicable results."""
        user = django_user_model.objects.create_user(email="na3@t.com", password="pw")
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        req_na = RequirementFactory(framework=fw, is_applicable=False)
        assessment = ComplianceAssessmentFactory(framework=fw, assessor=user)

        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.COMPLIANT,
            compliance_level=100, assessed_by=user,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req_na,
            compliance_status=ComplianceStatus.NOT_APPLICABLE,
            compliance_level=100, assessed_by=user,
        )

        assessment.recalculate_counts()
        assessment.refresh_from_db()
        assert assessment.not_applicable_count == 1
        assert assessment.compliant_count == 1
        assert assessment.total_requirements == 2


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
        assert "item-table-body" in content

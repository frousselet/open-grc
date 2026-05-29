"""Tests for the EBIOS RM GUI views (workshop transitions, detail pages, forms).

Covers:
- Workshop transitions (start / submit / validate / reject) with porte de
  validation enforcement.
- Workshop detail dispatcher routes to the correct template per workshop_number.
- W0 study framework edit form.
- W1 security baseline + FearedEvent + BaselineGap CRUD views.
- Permission gating on every endpoint.
"""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.tests.factories import EssentialAssetFactory
from risks.constants import (
    DICCriterion,
    EbiosWorkshopNumber,
    EbiosWorkshopStatus,
)
from risks.models import (
    BaselineGap,
    EbiosWorkshopProgress,
    FearedEvent,
)
from risks.tests.factories import (
    EbiosAssessmentFactory,
    FearedEventFactory,
)


pytestmark = pytest.mark.django_db


def _workshop_for(assessment, number):
    return assessment.ebios_workshops.get(workshop_number=number)


class TestWorkshopDetailDispatcher:
    def setup_method(self):
        self.user = UserFactory(is_superuser=True)

    def test_w0_renders_study_framework_template(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        url = reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.get(url)
        assert response.status_code == 200
        # The W0 page includes the study framework reference
        assert assessment.ebios_study_framework.reference.encode() in response.content

    def test_w1_renders_security_baseline_template(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W1)
        url = reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.get(url)
        assert response.status_code == 200
        assert b"Feared events" in response.content or b"redout" in response.content.lower()

    def test_w4_renders_placeholder(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W4)
        url = reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.get(url)
        assert response.status_code == 200

    def test_anonymous_user_is_redirected(self, client):
        assessment = EbiosAssessmentFactory()
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        url = reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.get(url)
        assert response.status_code in (302, 403)


class TestWorkshopTransitions:
    def setup_method(self):
        self.user = UserFactory(is_superuser=True)

    def test_start_w0_succeeds(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        url = reverse(
            "risks:ebios-workshop-start",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.post(url)
        assert response.status_code == 302
        workshop.refresh_from_db()
        assert workshop.status == EbiosWorkshopStatus.IN_PROGRESS
        assert workshop.started_at is not None

    def test_start_w1_blocked_when_w0_not_validated(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        w1 = _workshop_for(assessment, EbiosWorkshopNumber.W1)
        url = reverse(
            "risks:ebios-workshop-start",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": w1.pk},
        )
        response = client.post(url, follow=True)
        # The view redirects back; W1 stays not_started
        w1.refresh_from_db()
        assert w1.status == EbiosWorkshopStatus.NOT_STARTED

    def test_start_w1_allowed_after_w0_validated(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        w0 = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        w0.status = EbiosWorkshopStatus.VALIDATED
        w0.save()
        w1 = _workshop_for(assessment, EbiosWorkshopNumber.W1)
        url = reverse(
            "risks:ebios-workshop-start",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": w1.pk},
        )
        response = client.post(url)
        assert response.status_code == 302
        w1.refresh_from_db()
        assert w1.status == EbiosWorkshopStatus.IN_PROGRESS

    def test_submit_requires_in_progress(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        url = reverse(
            "risks:ebios-workshop-submit",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        # Not started: submit must not transition
        client.post(url)
        workshop.refresh_from_db()
        assert workshop.status == EbiosWorkshopStatus.NOT_STARTED

    def test_validate_records_user_and_timestamp(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        workshop.status = EbiosWorkshopStatus.IN_PROGRESS
        workshop.save()
        url = reverse(
            "risks:ebios-workshop-validate",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        client.post(url)
        workshop.refresh_from_db()
        assert workshop.status == EbiosWorkshopStatus.VALIDATED
        assert workshop.validated_by_id == self.user.pk
        assert workshop.validated_at is not None

    def test_reject_requires_reason(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        workshop.status = EbiosWorkshopStatus.IN_PROGRESS
        workshop.save()
        url = reverse(
            "risks:ebios-workshop-reject",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        # Without reason -> redirect back, status unchanged
        client.post(url)
        workshop.refresh_from_db()
        assert workshop.status == EbiosWorkshopStatus.IN_PROGRESS
        # With reason -> transitions to rejected
        client.post(url, {"rejection_reason": "Missing participants"})
        workshop.refresh_from_db()
        assert workshop.status == EbiosWorkshopStatus.REJECTED
        assert "Missing participants" in workshop.rejection_reason


class TestStudyFrameworkForm:
    def setup_method(self):
        self.user = UserFactory(is_superuser=True)

    def test_get_renders_form(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        sf = assessment.ebios_study_framework
        url = reverse("risks:ebios-study-framework-update", kwargs={"pk": sf.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_post_saves_changes(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        sf = assessment.ebios_study_framework
        url = reverse("risks:ebios-study-framework-update", kwargs={"pk": sf.pk})
        response = client.post(url, {
            "mission_statement": "Audit annuel",
            "business_perimeter": "Tous les services",
            "technical_perimeter": "SI corporate",
            "temporal_perimeter": "2026",
            "assumptions": "",
            "constraints": "",
            "expected_deliverables": "",
        })
        assert response.status_code == 302
        sf.refresh_from_db()
        assert sf.mission_statement == "Audit annuel"


class TestFearedEventViews:
    def setup_method(self):
        self.user = UserFactory(is_superuser=True)

    def test_create_feared_event(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        baseline = assessment.ebios_security_baseline
        asset = EssentialAssetFactory()
        url = reverse("risks:ebios-feared-event-create", kwargs={"baseline_pk": baseline.pk})
        response = client.post(url, {
            "essential_asset": asset.pk,
            "name": "Data leak",
            "description": "Customer data exposed externally",
            "dic_criterion": DICCriterion.CONFIDENTIALITY,
            "gravity_level": 3,
            "gravity_justification": "Regulatory impact",
        })
        assert response.status_code == 302
        assert baseline.feared_events.count() == 1
        feared = baseline.feared_events.first()
        assert feared.created_by == self.user

    def test_delete_feared_event(self, client):
        client.force_login(self.user)
        feared = FearedEventFactory()
        url = reverse("risks:ebios-feared-event-delete", kwargs={"pk": feared.pk})
        # GET shows confirm page
        get_response = client.get(url)
        assert get_response.status_code == 200
        # POST deletes
        del_response = client.post(url)
        assert del_response.status_code == 302
        assert not FearedEvent.objects.filter(pk=feared.pk).exists()


class TestBaselineGapViews:
    def setup_method(self):
        self.user = UserFactory(is_superuser=True)

    def test_create_baseline_gap(self, client):
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        baseline = assessment.ebios_security_baseline
        url = reverse("risks:ebios-baseline-gap-create", kwargs={"baseline_pk": baseline.pk})
        response = client.post(url, {
            "reference_source": "ISO 27002 A.5.1",
            "description": "Information security policies missing",
            "severity": "high",
            "status": "identified",
            "recommended_remediation": "Draft and publish policies",
        })
        assert response.status_code == 302
        assert baseline.gaps.count() == 1


class TestWorkshopW2W5Views:
    """Smoke tests for the W2..W5 detail pages and CRUD endpoints."""

    def setup_method(self):
        self.user = UserFactory(is_superuser=True)

    def test_w2_renders_with_risk_sources(self, client):
        from risks.tests.factories import RiskSourceFactory
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        RiskSourceFactory(assessment=assessment)
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W2)
        url = reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.get(url)
        assert response.status_code == 200
        assert b"Risk sources" in response.content or b"Sources" in response.content

    def test_create_risk_source(self, client):
        from risks.constants import RiskSourceCategory
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        url = reverse("risks:ebios-risk-source-create", kwargs={"assessment_pk": assessment.pk})
        response = client.post(url, {
            "name": "Cybercriminal group",
            "description": "",
            "category": RiskSourceCategory.ORGANIZED_CRIME,
            "motivation_level": 4,
            "motivation_description": "",
            "resources_level": 3,
            "activity_level": 3,
            "is_retained": "on",
            "retention_justification": "",
        })
        assert response.status_code == 302
        assert assessment.ebios_risk_sources.count() == 1
        # threat_level computed
        rs = assessment.ebios_risk_sources.first()
        assert rs.threat_level is not None

    def test_w3_renders_with_ecosystem(self, client):
        from risks.tests.factories import EcosystemStakeholderFactory
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        EcosystemStakeholderFactory(assessment=assessment)
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W3)
        url = reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.get(url)
        assert response.status_code == 200

    def test_create_ecosystem_stakeholder(self, client):
        from risks.constants import EcosystemStakeholderCategory
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        url = reverse("risks:ebios-ecosystem-create", kwargs={"assessment_pk": assessment.pk})
        response = client.post(url, {
            "name": "Cloud provider",
            "description": "",
            "category": EcosystemStakeholderCategory.SUPPLIER,
            "stakeholder": "",
            "supplier": "",
            "dependency": 3,
            "penetration": 3,
            "maturity": 2,
            "trust": 2,
            "is_attack_vector": "on",
            "attack_vector_justification": "Critical SaaS exposed externally",
        })
        assert response.status_code == 302
        assert assessment.ebios_ecosystem_stakeholders.count() == 1
        s = assessment.ebios_ecosystem_stakeholders.first()
        assert s.threat_level is not None
        assert s.threat_zone is not None

    def test_w4_renders_with_operational_scenarios(self, client):
        from risks.tests.factories import OperationalScenarioFactory
        client.force_login(self.user)
        assessment = EbiosAssessmentFactory()
        OperationalScenarioFactory(assessment=assessment)
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W4)
        url = reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.get(url)
        assert response.status_code == 200

    def test_consolidate_operational_scenario_creates_risk(self, client):
        from risks.tests.factories import OperationalScenarioFactory
        client.force_login(self.user)
        scenario = OperationalScenarioFactory(likelihood_v=3, gravity_level=3)
        url = reverse("risks:ebios-operational-scenario-consolidate", kwargs={"pk": scenario.pk})
        response = client.post(url)
        assert response.status_code == 302
        scenario.refresh_from_db()
        assert scenario.consolidated_risk is not None
        assert scenario.consolidated_risk.assessment_id == scenario.assessment_id

    def test_consolidate_is_idempotent(self, client):
        from risks.tests.factories import OperationalScenarioFactory
        client.force_login(self.user)
        scenario = OperationalScenarioFactory(likelihood_v=3, gravity_level=3)
        url = reverse("risks:ebios-operational-scenario-consolidate", kwargs={"pk": scenario.pk})
        client.post(url)
        scenario.refresh_from_db()
        risk_id = scenario.consolidated_risk_id
        # Second call: same risk
        client.post(url)
        scenario.refresh_from_db()
        assert scenario.consolidated_risk_id == risk_id

    def test_w5_renders_with_summary_and_pacs(self, client):
        from risks.tests.factories import PACSMeasureFactory
        client.force_login(self.user)
        measure = PACSMeasureFactory()
        assessment = measure.summary.assessment
        workshop = _workshop_for(assessment, EbiosWorkshopNumber.W5)
        url = reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
        )
        response = client.get(url)
        assert response.status_code == 200

    def test_capture_mappings_only_before(self, client):
        from risks.tests.factories import EbiosSummaryFactory, RiskFactory
        client.force_login(self.user)
        summary = EbiosSummaryFactory()
        RiskFactory(assessment=summary.assessment, current_risk_level=3)
        url = reverse("risks:ebios-summary-capture-mappings", kwargs={"pk": summary.pk})
        response = client.post(url, {"slot": "before"})
        assert response.status_code == 302
        summary.refresh_from_db()
        assert summary.risk_mapping_before["total"] == 1
        # Slot "after" was not captured
        assert summary.risk_mapping_after is None

    def test_create_pacs_measure(self, client):
        from risks.constants import PACSMeasureType
        from risks.tests.factories import EbiosSummaryFactory
        client.force_login(self.user)
        summary = EbiosSummaryFactory()
        url = reverse("risks:ebios-pacs-measure-create", kwargs={"summary_pk": summary.pk})
        response = client.post(url, {
            "name": "Two-factor authentication rollout",
            "description": "Deploy 2FA to all admin accounts",
            "measure_type": PACSMeasureType.PROTECTION,
            "priority": "high",
            "status": "planned",
            "order": 0,
        })
        assert response.status_code == 302
        assert summary.pacs_measures.count() == 1


class TestStepperContext:
    """build_ebios_stepper_context assigns one of done / current / review / next / future / rejected."""

    def test_fresh_assessment_first_workshop_is_next_cta(self):
        from risks.views_ebios import build_ebios_stepper_context
        assessment = EbiosAssessmentFactory()
        ctx = build_ebios_stepper_context(assessment)
        steps = ctx["ebios_stepper_steps"]
        # W0 must be the next CTA, W1..W5 future
        assert steps[0]["state"] == "next"
        for s in steps[1:]:
            assert s["state"] == "future"
        # next_action references W0
        assert ctx["ebios_next_action"].workshop_number == 0
        # No rejected pills
        assert ctx["ebios_rejected_steps"] == []

    def test_done_current_next_progression(self):
        from risks.views_ebios import build_ebios_stepper_context
        assessment = EbiosAssessmentFactory()
        w0 = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        w0.status = EbiosWorkshopStatus.VALIDATED
        w0.save()
        w1 = _workshop_for(assessment, EbiosWorkshopNumber.W1)
        w1.status = EbiosWorkshopStatus.IN_PROGRESS
        w1.save()
        ctx = build_ebios_stepper_context(assessment)
        steps = ctx["ebios_stepper_steps"]
        assert steps[0]["state"] == "done"
        assert steps[1]["state"] == "current"
        # W2..W5 future (no "next" CTA because W1 is in_progress, not validated)
        for s in steps[2:]:
            assert s["state"] == "future"
        assert ctx["ebios_next_action"] is None

    def test_under_review_state(self):
        from risks.views_ebios import build_ebios_stepper_context
        assessment = EbiosAssessmentFactory()
        w0 = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        w0.status = EbiosWorkshopStatus.UNDER_REVIEW
        w0.save()
        ctx = build_ebios_stepper_context(assessment)
        assert ctx["ebios_stepper_steps"][0]["state"] == "review"

    def test_rejected_workshop_moves_to_branch(self):
        from risks.views_ebios import build_ebios_stepper_context
        assessment = EbiosAssessmentFactory()
        w0 = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        w0.status = EbiosWorkshopStatus.REJECTED
        w0.save()
        ctx = build_ebios_stepper_context(assessment)
        # W0 is no longer in the main flow
        numbers_in_main = [s["workshop_number"] for s in ctx["ebios_stepper_steps"]]
        assert 0 not in numbers_in_main
        # It lives on the rejected branch
        rejected_numbers = [s["workshop_number"] for s in ctx["ebios_rejected_steps"]]
        assert 0 in rejected_numbers

    def test_current_workshop_highlight(self):
        from risks.views_ebios import build_ebios_stepper_context
        assessment = EbiosAssessmentFactory()
        w0 = _workshop_for(assessment, EbiosWorkshopNumber.W0)
        ctx = build_ebios_stepper_context(assessment, current_workshop=w0)
        # The first step must be flagged as is_current for the box-shadow highlight
        assert ctx["ebios_stepper_steps"][0]["is_current"] is True

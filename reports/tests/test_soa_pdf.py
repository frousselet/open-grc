"""Tests for the enriched Statement of Applicability PDF generator.

These tests exercise the data-building logic (`build_soa_frameworks_data`)
and the HTML template rendering directly, so they do not depend on a
working weasyprint install.
"""

from unittest.mock import patch

import pytest
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.tests.factories import UserFactory
from compliance.models import Framework
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from reports.generators import build_soa_frameworks_data, generate_soa_pdf
from risks.tests.factories import RiskFactory


pytestmark = pytest.mark.django_db


def _render_template(frameworks_data, user):
    return render_to_string("reports/soa_pdf.html", {
        "frameworks_data": frameworks_data,
        "generated_at": timezone.now(),
        "generated_by": user,
        "company": None,
    })


class TestBuildSoaFrameworksData:
    def test_returns_one_dict_per_framework(self):
        fw1 = FrameworkFactory(is_approved=True)
        fw2 = FrameworkFactory(is_approved=True)
        RequirementFactory(is_approved=True, framework=fw1, requirement_number="A.1")
        RequirementFactory(is_approved=True, framework=fw2, requirement_number="A.2")
        data = build_soa_frameworks_data(
            Framework.objects.filter(pk__in=[fw1.pk, fw2.pk])
        )
        assert len(data) == 2
        for entry in data:
            assert {"framework", "rows", "linked_risk_count"} <= entry.keys()

    def test_row_includes_structured_risks_data(self):
        fw = FrameworkFactory(is_approved=True)
        req = RequirementFactory(is_approved=True, framework=fw, requirement_number="A.5.2")
        risk = RiskFactory(name="Data leak", is_approved=True)
        risk.residual_risk_level = 2
        risk.treatment_decision = "mitigate"
        risk.save()
        risk.linked_requirements.add(req)

        data = build_soa_frameworks_data(Framework.objects.filter(pk=fw.pk))
        assert len(data) == 1
        rows = data[0]["rows"]
        assert len(rows) == 1
        risks_data = rows[0]["risks_data"]
        assert risks_data == [{
            "reference": risk.reference,
            "name": "Data leak",
            "current_risk_level": risk.current_risk_level,
            "residual_risk_level": 2,
            "treatment_decision": risk.get_treatment_decision_display(),
            "treatment_decision_key": "mitigate",
            "status": risk.get_status_display(),
        }]

    def test_linked_risk_count_is_deduplicated(self):
        fw = FrameworkFactory(is_approved=True)
        r1 = RequirementFactory(is_approved=True, framework=fw, requirement_number="A.5.5")
        r2 = RequirementFactory(is_approved=True, framework=fw, requirement_number="A.5.6")
        risk_a = RiskFactory(is_approved=True)
        risk_b = RiskFactory(is_approved=True)
        risk_a.linked_requirements.add(r1, r2)
        risk_b.linked_requirements.add(r2)

        data = build_soa_frameworks_data(Framework.objects.filter(pk=fw.pk))
        assert data[0]["linked_risk_count"] == 2

    def test_applicable_with_no_plan_uses_risk_justification(self):
        fw = FrameworkFactory(is_approved=True)
        req = RequirementFactory(is_approved=True, framework=fw, requirement_number="A.5.7")
        risk = RiskFactory(is_approved=True)
        risk.linked_requirements.add(req)

        data = build_soa_frameworks_data(Framework.objects.filter(pk=fw.pk))
        assert data[0]["rows"][0]["justification"] == "Selected to address linked risks."

    def test_non_validated_elements_are_excluded(self):
        """Draft frameworks, requirements and risks never appear in the SoA (RG-LC-01)."""
        draft_fw = FrameworkFactory()
        fw = FrameworkFactory(is_approved=True)
        RequirementFactory(framework=fw, requirement_number="A.9.1")  # draft
        req = RequirementFactory(is_approved=True, framework=fw, requirement_number="A.9.2")
        draft_risk = RiskFactory()
        draft_risk.linked_requirements.add(req)

        data = build_soa_frameworks_data(
            Framework.objects.filter(pk__in=[draft_fw.pk, fw.pk])
        )
        assert len(data) == 1  # the draft framework is excluded
        rows = data[0]["rows"]
        assert [r["number"] for r in rows] == ["A.9.2"]  # the draft requirement too
        assert rows[0]["risks_data"] == []  # and the draft linked risk
        assert data[0]["linked_risk_count"] == 0

    def test_non_applicable_uses_applicability_justification(self):
        fw = FrameworkFactory(is_approved=True)
        req = RequirementFactory(
            framework=fw,
            requirement_number="A.5.8",
            is_applicable=False,
            is_approved=True,
            applicability_justification="Out of scope for hosted-only operations.",
        )
        data = build_soa_frameworks_data(Framework.objects.filter(pk=fw.pk))
        assert data[0]["rows"][0]["justification"] == (
            "Out of scope for hosted-only operations."
        )


class TestSoaTemplateRendering:
    def test_residual_pill_colors_by_level(self):
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, requirement_number="A.5.3")
        # Render with hand-built risks_data so we can assert on the pill
        # classes without depending on factory state.
        rendered = _render_template([{
            "framework": fw,
            "rows": [{
                "number": req.requirement_number,
                "name": req.name,
                "is_applicable": True,
                "justification": "",
                "risks_data": [
                    {"reference": "R1", "name": "High", "current_risk_level": None,
                     "residual_risk_level": 4, "treatment_decision": "",
                     "treatment_decision_key": "", "status": ""},
                    {"reference": "R2", "name": "Med", "current_risk_level": None,
                     "residual_risk_level": 3, "treatment_decision": "",
                     "treatment_decision_key": "", "status": ""},
                    {"reference": "R3", "name": "Low", "current_risk_level": None,
                     "residual_risk_level": 1, "treatment_decision": "",
                     "treatment_decision_key": "", "status": ""},
                ],
            }],
            "linked_risk_count": 3,
        }], UserFactory(is_superuser=True))
        assert "residual-high" in rendered
        assert "residual-med" in rendered
        assert "residual-low" in rendered

    def test_unknown_residual_renders_unknown_pill(self):
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, requirement_number="A.5.4")
        rendered = _render_template([{
            "framework": fw,
            "rows": [{
                "number": req.requirement_number,
                "name": req.name,
                "is_applicable": True,
                "justification": "",
                "risks_data": [{
                    "reference": "R1", "name": "Unscored",
                    "current_risk_level": None, "residual_risk_level": None,
                    "treatment_decision": "", "treatment_decision_key": "",
                    "status": "",
                }],
            }],
            "linked_risk_count": 1,
        }], UserFactory(is_superuser=True))
        assert "residual-unknown" in rendered

    def test_treatment_decision_label_surfaces_in_output(self):
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, requirement_number="A.5.9")
        rendered = _render_template([{
            "framework": fw,
            "rows": [{
                "number": req.requirement_number,
                "name": req.name,
                "is_applicable": True,
                "justification": "",
                "risks_data": [{
                    "reference": "R1", "name": "Sample",
                    "current_risk_level": None, "residual_risk_level": 1,
                    "treatment_decision": "Mitigate",
                    "treatment_decision_key": "mitigate",
                    "status": "",
                }],
            }],
            "linked_risk_count": 1,
        }], UserFactory(is_superuser=True))
        assert "Mitigate" in rendered

    def test_framework_summary_count(self):
        fw = FrameworkFactory()
        rendered = _render_template([{
            "framework": fw, "rows": [], "linked_risk_count": 2,
        }], UserFactory(is_superuser=True))
        assert "2 risks addressed" in rendered or "2 risk addressed" in rendered


class TestGenerateSoaPdfSmoke:
    """End-to-end smoke test with weasyprint mocked."""

    def test_returns_filename_and_bytes(self):
        user = UserFactory(is_superuser=True)
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, requirement_number="A.10.1")
        with patch("reports.generators.HTML", create=True) as html_cls:
            html_cls.return_value.write_pdf.return_value = b"%PDF-fake"
            # Patch weasyprint import path the function uses.
            with patch.dict(
                "sys.modules",
                {"weasyprint": __import__("types").SimpleNamespace(HTML=html_cls)},
            ):
                filename, content = generate_soa_pdf(
                    Framework.objects.filter(pk=fw.pk), user,
                )
        assert filename.startswith("SoA_") and filename.endswith(".pdf")
        assert content == b"%PDF-fake"

"""Tests for MCP compliance tools stats/status propagation.

Verifies that creating/updating/deleting findings and assessment results
via MCP correctly triggers recalculate_counts() and apply_findings_to_results().
"""

import json

import pytest

from accounts.tests.factories import UserFactory
from compliance.constants import (
    AssessmentStatus,
    ComplianceStatus,
    FindingType,
)
from compliance.models.assessment import AssessmentResult, ComplianceAssessment
from compliance.tests.factories import (
    AssessmentResultFactory,
    ComplianceAssessmentFactory,
    FindingFactory,
    FrameworkFactory,
    RequirementFactory,
)
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db


def _call_tool(srv, user, tool_name, arguments):
    result = srv.handle_request(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }), user)
    raw = result["result"]["content"][0]["text"]
    return json.loads(raw)


class TestFindingStatsPropagate:
    """Creating/updating/deleting findings via MCP updates assessment stats."""

    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)
        self.fw = FrameworkFactory()
        self.req = RequirementFactory(framework=self.fw)
        self.assessment = ComplianceAssessmentFactory(
            assessor=self.user, frameworks=[self.fw],
            status=AssessmentStatus.IN_PROGRESS,
        )
        self.assessment.sync_results(self.user)

    def test_create_finding_updates_result_status(self):
        result = self.assessment.results.get(requirement=self.req)
        assert result.compliance_status == ComplianceStatus.NOT_ASSESSED

        _call_tool(self.srv, self.user, "create_finding", {
            "assessment_id": str(self.assessment.pk),
            "finding_type": "major_nc",
            "description": "Major NC finding",
            "assessor_id": str(self.user.pk),
            "requirement_ids": [str(self.req.pk)],
        })

        result.refresh_from_db()
        assert result.compliance_status == ComplianceStatus.MAJOR_NON_CONFORMITY
        assert result.compliance_level == 0

    def test_create_finding_updates_assessment_counts(self):
        _call_tool(self.srv, self.user, "create_finding", {
            "assessment_id": str(self.assessment.pk),
            "finding_type": "major_nc",
            "description": "Major NC",
            "assessor_id": str(self.user.pk),
            "requirement_ids": [str(self.req.pk)],
        })

        self.assessment.refresh_from_db()
        assert self.assessment.major_non_conformity_count == 1

    def test_update_finding_type_updates_stats(self):
        finding = FindingFactory(
            assessment=self.assessment,
            finding_type=FindingType.MAJOR_NON_CONFORMITY,
            assessor=self.user,
        )
        finding.requirements.add(self.req)
        self.assessment.apply_findings_to_results()

        _call_tool(self.srv, self.user, "update_finding", {
            "id": str(finding.pk),
            "finding_type": "strength",
        })

        self.assessment.refresh_from_db()
        assert self.assessment.major_non_conformity_count == 0
        assert self.assessment.strength_count == 1

        result = self.assessment.results.get(requirement=self.req)
        assert result.compliance_status == ComplianceStatus.STRENGTH

    def test_delete_finding_resets_result(self):
        finding = FindingFactory(
            assessment=self.assessment,
            finding_type=FindingType.OBSERVATION,
            assessor=self.user,
        )
        finding.requirements.add(self.req)
        self.assessment.apply_findings_to_results()

        result = self.assessment.results.get(requirement=self.req)
        assert result.compliance_status == ComplianceStatus.OBSERVATION

        _call_tool(self.srv, self.user, "delete_finding", {
            "id": str(finding.pk),
        })

        result.refresh_from_db()
        assert result.compliance_status == ComplianceStatus.NOT_ASSESSED

        self.assessment.refresh_from_db()
        assert self.assessment.observation_count == 0


class TestAssessmentResultStatsPropagate:
    """Creating/updating/deleting assessment results via MCP recalculates counts."""

    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)
        self.fw = FrameworkFactory()
        self.req = RequirementFactory(framework=self.fw)
        self.assessment = ComplianceAssessmentFactory(
            assessor=self.user, frameworks=[self.fw],
        )
        self.assessment.sync_results(self.user)

    def test_update_result_recalculates_counts(self):
        result = self.assessment.results.get(requirement=self.req)
        assert self.assessment.not_assessed_count == 1

        _call_tool(self.srv, self.user, "update_assessment_result", {
            "id": str(result.pk),
            "compliance_status": ComplianceStatus.COMPLIANT,
            "compliance_level": "100",
        })

        self.assessment.refresh_from_db()
        assert self.assessment.compliant_count == 1
        assert self.assessment.not_assessed_count == 0

    def test_delete_result_recalculates_counts(self):
        self.assessment.refresh_from_db()
        assert self.assessment.total_requirements == 1

        result = self.assessment.results.get(requirement=self.req)
        _call_tool(self.srv, self.user, "delete_assessment_result", {
            "id": str(result.pk),
        })

        self.assessment.refresh_from_db()
        assert self.assessment.total_requirements == 0

    def test_create_result_recalculates_counts(self):
        req2 = RequirementFactory(framework=self.fw)
        content = _call_tool(self.srv, self.user, "create_assessment_result", {
            "assessment_id": str(self.assessment.pk),
            "requirement_id": str(req2.pk),
            "compliance_status": ComplianceStatus.COMPLIANT,
            "compliance_level": "100",
            "assessed_by_id": str(self.user.pk),
            "assessed_at": "2026-03-14T10:00:00Z",
        })
        assert "error" not in json.dumps(content)

        self.assessment.refresh_from_db()
        assert self.assessment.total_requirements == 2
        assert self.assessment.compliant_count == 1


class TestAssessmentStatusTransition:
    """Status changes via MCP use transition_to() with workflow validation."""

    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_valid_transition_draft_to_planned(self):
        assessment = ComplianceAssessmentFactory(
            assessor=self.user, status=AssessmentStatus.DRAFT,
        )
        content = _call_tool(self.srv, self.user, "update_compliance_assessment", {
            "id": str(assessment.pk),
            "status": "planned",
        })
        assert "error" not in content
        assessment.refresh_from_db()
        assert assessment.status == AssessmentStatus.PLANNED

    def test_invalid_transition_draft_to_completed(self):
        assessment = ComplianceAssessmentFactory(
            assessor=self.user, status=AssessmentStatus.DRAFT,
        )
        content = _call_tool(self.srv, self.user, "update_compliance_assessment", {
            "id": str(assessment.pk),
            "status": "completed",
        })
        assert "error" in json.dumps(content)
        assessment.refresh_from_db()
        assert assessment.status == AssessmentStatus.DRAFT

    def test_completed_transition_resets_evaluated_without_findings(self):
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw)
        req2 = RequirementFactory(framework=fw)
        assessment = ComplianceAssessmentFactory(
            assessor=self.user, frameworks=[fw],
            status=AssessmentStatus.IN_PROGRESS,
        )
        assessment.sync_results(self.user)

        # Mark both as EVALUATED
        for result in assessment.results.all():
            result.compliance_status = ComplianceStatus.EVALUATED
            result.save()

        # Add a finding only to req1
        finding = FindingFactory(
            assessment=assessment, assessor=self.user,
            finding_type=FindingType.MINOR_NON_CONFORMITY,
        )
        finding.requirements.add(req1)

        # Transition to COMPLETED
        content = _call_tool(self.srv, self.user, "update_compliance_assessment", {
            "id": str(assessment.pk),
            "status": "completed",
        })
        assert "error" not in content

        assessment.refresh_from_db()
        assert assessment.status == AssessmentStatus.COMPLETED

        # req2 (no finding) should be reset to NOT_ASSESSED
        r2 = assessment.results.get(requirement=req2)
        assert r2.compliance_status == ComplianceStatus.NOT_ASSESSED

    def test_full_workflow_transition(self):
        assessment = ComplianceAssessmentFactory(
            assessor=self.user, status=AssessmentStatus.DRAFT,
        )
        for status in ["planned", "in_progress", "completed", "closed"]:
            content = _call_tool(self.srv, self.user, "update_compliance_assessment", {
                "id": str(assessment.pk),
                "status": status,
            })
            assert "error" not in content
            assessment.refresh_from_db()
            assert assessment.status == status

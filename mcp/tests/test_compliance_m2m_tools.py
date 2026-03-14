"""Tests for MCP compliance tools with M2M support (framework_ids, requirement_ids)."""

import json

import pytest

from accounts.tests.factories import UserFactory
from compliance.constants import FindingType
from compliance.tests.factories import (
    ComplianceAssessmentFactory,
    FindingFactory,
    FrameworkFactory,
    RequirementFactory,
)
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db


def _call_tool(srv, user, tool_name, arguments):
    """Helper to call an MCP tool and return parsed result content."""
    result = srv.handle_request(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }), user)
    raw = result["result"]["content"][0]["text"]
    return json.loads(raw)


class TestCreateComplianceAssessmentWithFrameworks:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_create_without_framework_ids(self):
        content = _call_tool(self.srv, self.user, "create_compliance_assessment", {
            "name": "Test Assessment",
            "assessor_id": str(self.user.pk),
        })
        assert "error" not in content
        assert content["name"] == "Test Assessment"

    def test_create_with_framework_ids(self):
        fw1 = FrameworkFactory()
        fw2 = FrameworkFactory()
        RequirementFactory(framework=fw1)
        RequirementFactory(framework=fw1)
        RequirementFactory(framework=fw2)

        content = _call_tool(self.srv, self.user, "create_compliance_assessment", {
            "name": "Assessment with FW",
            "assessor_id": str(self.user.pk),
            "framework_ids": [str(fw1.pk), str(fw2.pk)],
        })
        assert "error" not in content

        from compliance.models.assessment import ComplianceAssessment
        assessment = ComplianceAssessment.objects.get(pk=content["id"])
        assert set(assessment.frameworks.values_list("pk", flat=True)) == {fw1.pk, fw2.pk}
        # sync_results should have created 3 results
        assert assessment.results.count() == 3

    def test_create_with_invalid_framework_id(self):
        content = _call_tool(self.srv, self.user, "create_compliance_assessment", {
            "name": "Bad FW",
            "assessor_id": str(self.user.pk),
            "framework_ids": ["00000000-0000-0000-0000-000000000000"],
        })
        assert content.get("isError") or "error" in json.dumps(content)


class TestUpdateComplianceAssessmentWithFrameworks:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_update_adds_frameworks(self):
        assessment = ComplianceAssessmentFactory(assessor=self.user)
        fw = FrameworkFactory()
        RequirementFactory(framework=fw)

        content = _call_tool(self.srv, self.user, "update_compliance_assessment", {
            "id": str(assessment.pk),
            "framework_ids": [str(fw.pk)],
        })
        assert "error" not in content

        assessment.refresh_from_db()
        assert fw in assessment.frameworks.all()
        assert assessment.results.count() == 1

    def test_update_replaces_frameworks(self):
        fw1 = FrameworkFactory()
        fw2 = FrameworkFactory()
        RequirementFactory(framework=fw1)
        RequirementFactory(framework=fw2)
        assessment = ComplianceAssessmentFactory(assessor=self.user, frameworks=[fw1])
        assessment.sync_results(self.user)
        assert assessment.results.count() == 1

        content = _call_tool(self.srv, self.user, "update_compliance_assessment", {
            "id": str(assessment.pk),
            "framework_ids": [str(fw2.pk)],
        })
        assert "error" not in content

        assessment.refresh_from_db()
        assert list(assessment.frameworks.all()) == [fw2]
        assert assessment.results.count() == 1

    def test_update_without_framework_ids_keeps_existing(self):
        fw = FrameworkFactory()
        assessment = ComplianceAssessmentFactory(assessor=self.user, frameworks=[fw])

        content = _call_tool(self.srv, self.user, "update_compliance_assessment", {
            "id": str(assessment.pk),
            "name": "Updated Name",
        })
        assert "error" not in content

        assessment.refresh_from_db()
        assert assessment.name == "Updated Name"
        assert fw in assessment.frameworks.all()


class TestCreateFindingWithRequirements:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)
        self.assessment = ComplianceAssessmentFactory(assessor=self.user)

    def test_create_without_requirement_ids(self):
        content = _call_tool(self.srv, self.user, "create_finding", {
            "assessment_id": str(self.assessment.pk),
            "finding_type": "major_nc",
            "description": "Test finding",
            "assessor_id": str(self.user.pk),
        })
        assert "error" not in content
        assert content["finding_type"] == "major_nc"

    def test_create_with_requirement_ids(self):
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw)
        req2 = RequirementFactory(framework=fw)

        content = _call_tool(self.srv, self.user, "create_finding", {
            "assessment_id": str(self.assessment.pk),
            "finding_type": "minor_nc",
            "description": "Finding with reqs",
            "assessor_id": str(self.user.pk),
            "requirement_ids": [str(req1.pk), str(req2.pk)],
        })
        assert "error" not in content

        from compliance.models.finding import Finding
        finding = Finding.objects.get(pk=content["id"])
        assert finding.requirements.count() == 2
        assert set(finding.requirements.values_list("pk", flat=True)) == {req1.pk, req2.pk}

    def test_create_with_invalid_requirement_id(self):
        content = _call_tool(self.srv, self.user, "create_finding", {
            "assessment_id": str(self.assessment.pk),
            "finding_type": "observation",
            "description": "Bad reqs",
            "assessor_id": str(self.user.pk),
            "requirement_ids": ["00000000-0000-0000-0000-000000000000"],
        })
        assert content.get("isError") or "error" in json.dumps(content)


class TestUpdateFindingWithRequirements:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_update_adds_requirements(self):
        finding = FindingFactory(assessor=self.user)
        req = RequirementFactory()

        content = _call_tool(self.srv, self.user, "update_finding", {
            "id": str(finding.pk),
            "requirement_ids": [str(req.pk)],
        })
        assert "error" not in content

        finding.refresh_from_db()
        assert req in finding.requirements.all()

    def test_update_replaces_requirements(self):
        req1 = RequirementFactory()
        req2 = RequirementFactory()
        finding = FindingFactory(assessor=self.user)
        finding.requirements.add(req1)

        content = _call_tool(self.srv, self.user, "update_finding", {
            "id": str(finding.pk),
            "requirement_ids": [str(req2.pk)],
        })
        assert "error" not in content

        finding.refresh_from_db()
        assert list(finding.requirements.all()) == [req2]

    def test_update_clears_requirements(self):
        req = RequirementFactory()
        finding = FindingFactory(assessor=self.user)
        finding.requirements.add(req)

        content = _call_tool(self.srv, self.user, "update_finding", {
            "id": str(finding.pk),
            "requirement_ids": [],
        })
        assert "error" not in content

        finding.refresh_from_db()
        assert finding.requirements.count() == 0

    def test_update_without_requirement_ids_keeps_existing(self):
        req = RequirementFactory()
        finding = FindingFactory(assessor=self.user)
        finding.requirements.add(req)

        content = _call_tool(self.srv, self.user, "update_finding", {
            "id": str(finding.pk),
            "description": "Updated desc",
        })
        assert "error" not in content

        finding.refresh_from_db()
        assert finding.description == "Updated desc"
        assert req in finding.requirements.all()


class TestFindingTypeEnumSchema:
    def test_finding_type_enum_in_create_schema(self):
        srv = McpServer()
        register_all_tools(srv)
        schema = srv._tools["create_finding"]["inputSchema"]
        ft_prop = schema["properties"]["finding_type"]
        assert "enum" in ft_prop
        assert set(ft_prop["enum"]) == {"major_nc", "minor_nc", "observation", "improvement", "strength"}

    def test_finding_type_enum_in_update_schema(self):
        srv = McpServer()
        register_all_tools(srv)
        schema = srv._tools["update_finding"]["inputSchema"]
        ft_prop = schema["properties"]["finding_type"]
        assert "enum" in ft_prop
        assert set(ft_prop["enum"]) == {"major_nc", "minor_nc", "observation", "improvement", "strength"}

    def test_framework_ids_in_create_assessment_schema(self):
        srv = McpServer()
        register_all_tools(srv)
        schema = srv._tools["create_compliance_assessment"]["inputSchema"]
        assert "framework_ids" in schema["properties"]
        assert schema["properties"]["framework_ids"]["type"] == "array"

    def test_framework_ids_in_update_assessment_schema(self):
        srv = McpServer()
        register_all_tools(srv)
        schema = srv._tools["update_compliance_assessment"]["inputSchema"]
        assert "framework_ids" in schema["properties"]
        assert schema["properties"]["framework_ids"]["type"] == "array"

    def test_requirement_ids_in_create_finding_schema(self):
        srv = McpServer()
        register_all_tools(srv)
        schema = srv._tools["create_finding"]["inputSchema"]
        assert "requirement_ids" in schema["properties"]
        assert schema["properties"]["requirement_ids"]["type"] == "array"

    def test_requirement_ids_in_update_finding_schema(self):
        srv = McpServer()
        register_all_tools(srv)
        schema = srv._tools["update_finding"]["inputSchema"]
        assert "requirement_ids" in schema["properties"]
        assert schema["properties"]["requirement_ids"]["type"] == "array"

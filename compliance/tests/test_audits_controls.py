import pytest

from compliance.constants import (
    AuditStatus,
    AuditType,
    ControlFrequency,
    ControlResult,
    ControlStatus,
)
from compliance.tests.factories import (
    AuditorFactory,
    ComplianceAuditFactory,
    ComplianceControlFactory,
    ControlBodyFactory,
    FrameworkFactory,
)

pytestmark = pytest.mark.django_db


class TestComplianceControl:
    def test_create_control(self):
        control = ComplianceControlFactory()
        assert control.reference.startswith("CTRL-")
        assert control.status == ControlStatus.PLANNED
        assert control.result == ControlResult.NOT_ASSESSED

    def test_control_str(self):
        control = ComplianceControlFactory(name="Access review")
        assert "Access review" in str(control)
        assert control.reference in str(control)

    def test_control_frequency(self):
        control = ComplianceControlFactory(frequency=ControlFrequency.MONTHLY)
        assert control.frequency == ControlFrequency.MONTHLY


class TestComplianceAudit:
    def test_create_audit(self):
        audit = ComplianceAuditFactory()
        assert audit.reference.startswith("AUDT-")
        assert audit.status == AuditStatus.PLANNED
        assert audit.audit_type == AuditType.FIRST_PARTY

    def test_audit_str(self):
        audit = ComplianceAuditFactory(name="Annual audit 2026")
        assert "Annual audit 2026" in str(audit)

    def test_audit_with_frameworks(self):
        fw1 = FrameworkFactory()
        fw2 = FrameworkFactory()
        audit = ComplianceAuditFactory()
        audit.frameworks.add(fw1, fw2)
        assert audit.frameworks.count() == 2

    def test_audit_types(self):
        audit_1p = ComplianceAuditFactory(audit_type=AuditType.FIRST_PARTY)
        audit_2p = ComplianceAuditFactory(audit_type=AuditType.SECOND_PARTY)
        audit_3p = ComplianceAuditFactory(audit_type=AuditType.THIRD_PARTY)
        assert audit_1p.audit_type == "first_party"
        assert audit_2p.audit_type == "second_party"
        assert audit_3p.audit_type == "third_party"


class TestControlBody:
    def test_create_control_body(self):
        cb = ControlBodyFactory()
        assert cb.reference.startswith("CBDY-")
        assert cb.is_accredited is True

    def test_control_body_str(self):
        cb = ControlBodyFactory(name="Bureau Veritas")
        assert "Bureau Veritas" in str(cb)

    def test_control_body_with_frameworks(self):
        fw = FrameworkFactory()
        cb = ControlBodyFactory()
        cb.frameworks.add(fw)
        assert cb.frameworks.count() == 1

    def test_control_body_linked_to_audit(self):
        cb = ControlBodyFactory()
        audit = ComplianceAuditFactory(
            control_body=cb,
            audit_type=AuditType.THIRD_PARTY,
        )
        assert audit.control_body == cb
        assert cb.audits.count() == 1


class TestAuditor:
    def test_create_auditor(self):
        auditor = AuditorFactory()
        assert auditor.reference.startswith("AUDR-")
        assert auditor.control_body is not None

    def test_auditor_str(self):
        auditor = AuditorFactory(first_name="Jean", last_name="Dupont")
        assert "Jean" in str(auditor)
        assert "Dupont" in str(auditor)

    def test_multiple_auditors_per_body(self):
        cb = ControlBodyFactory()
        a1 = AuditorFactory(control_body=cb, certifications="ISO 27001")
        a2 = AuditorFactory(control_body=cb, certifications="ISO 22301")
        assert cb.auditors.count() == 2
        assert a1.certifications != a2.certifications

import factory

from accounts.tests.factories import UserFactory
from compliance.constants import (
    AuditStatus,
    AuditType,
    ComplianceStatus,
    ControlFrequency,
    ControlResult,
    ControlStatus,
    FrameworkCategory,
    FrameworkType,
    MappingType,
    RequirementType,
)
from compliance.models.audit import ComplianceAudit
from compliance.models.control import ComplianceControl
from compliance.models.control_body import Auditor, ControlBody
from compliance.models.framework import Framework
from compliance.models.mapping import RequirementMapping
from compliance.models.requirement import Requirement


class FrameworkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Framework

    name = factory.Sequence(lambda n: f"Framework {n}")
    type = FrameworkType.STANDARD
    category = FrameworkCategory.INFORMATION_SECURITY
    owner = factory.SubFactory(UserFactory)


class RequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Requirement

    framework = factory.SubFactory(FrameworkFactory)
    requirement_number = factory.Sequence(lambda n: f"REQ-{n:03d}")
    name = factory.Sequence(lambda n: f"Requirement {n}")
    description = "Test requirement"
    type = RequirementType.MANDATORY
    is_applicable = True
    compliance_status = ComplianceStatus.NOT_ASSESSED
    compliance_level = 0


class MappingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RequirementMapping

    source_requirement = factory.SubFactory(RequirementFactory)
    target_requirement = factory.SubFactory(RequirementFactory)
    mapping_type = MappingType.EQUIVALENT


class ComplianceControlFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ComplianceControl

    name = factory.Sequence(lambda n: f"Control {n}")
    description = "Test control"
    frequency = ControlFrequency.QUARTERLY
    status = ControlStatus.PLANNED
    result = ControlResult.NOT_ASSESSED
    owner = factory.SubFactory(UserFactory)


class ControlBodyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ControlBody

    name = factory.Sequence(lambda n: f"Control Body {n}")
    description = "Test control body"
    is_accredited = True
    country = "France"


class ComplianceAuditFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ComplianceAudit

    name = factory.Sequence(lambda n: f"Audit {n}")
    description = "Test audit"
    audit_type = AuditType.FIRST_PARTY
    status = AuditStatus.PLANNED
    lead_auditor = factory.SubFactory(UserFactory)


class AuditorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Auditor

    first_name = factory.Sequence(lambda n: f"Auditor{n}")
    last_name = factory.Sequence(lambda n: f"LastName{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name.lower()}@example.com")
    control_body = factory.SubFactory(ControlBodyFactory)
    certifications = "ISO 27001 Lead Auditor"

import factory
from django.utils import timezone

from accounts.tests.factories import UserFactory
from compliance.constants import (
    AssessmentStatus,
    ComplianceStatus,
    FrameworkCategory,
    FrameworkType,
    MappingType,
    RequirementType,
)
from compliance.models.assessment import AssessmentResult, ComplianceAssessment
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


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "compliance.Section"

    framework = factory.SubFactory(FrameworkFactory)
    name = factory.Sequence(lambda n: f"Section {n}")
    order = factory.Sequence(lambda n: n)


class ComplianceAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ComplianceAssessment

    framework = factory.SubFactory(FrameworkFactory)
    name = factory.Sequence(lambda n: f"Assessment {n}")
    assessment_date = factory.LazyFunction(lambda: timezone.now().date())
    assessor = factory.SubFactory(UserFactory)
    status = AssessmentStatus.DRAFT


class AssessmentResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssessmentResult

    assessment = factory.SubFactory(ComplianceAssessmentFactory)
    requirement = factory.SubFactory(RequirementFactory)
    compliance_status = ComplianceStatus.NOT_ASSESSED
    compliance_level = 0
    assessed_by = factory.SubFactory(UserFactory)
    assessed_at = factory.LazyFunction(timezone.now)


class MappingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RequirementMapping

    source_requirement = factory.SubFactory(RequirementFactory)
    target_requirement = factory.SubFactory(RequirementFactory)
    mapping_type = MappingType.EQUIVALENT

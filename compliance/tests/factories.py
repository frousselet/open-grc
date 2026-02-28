import factory

from accounts.tests.factories import UserFactory
from compliance.constants import (
    ComplianceStatus,
    FrameworkCategory,
    FrameworkType,
    MappingType,
    RequirementType,
)
from compliance.models.framework import Framework
from compliance.models.mapping import RequirementMapping
from compliance.models.requirement import Requirement


class FrameworkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Framework

    reference = factory.Sequence(lambda n: f"FW-{n:03d}")
    name = factory.Sequence(lambda n: f"Framework {n}")
    type = FrameworkType.STANDARD
    category = FrameworkCategory.INFORMATION_SECURITY
    owner = factory.SubFactory(UserFactory)


class RequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Requirement

    framework = factory.SubFactory(FrameworkFactory)
    reference = factory.Sequence(lambda n: f"REQ-{n:03d}")
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

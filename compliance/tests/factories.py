import factory
from datetime import timedelta
from django.utils import timezone

from accounts.tests.factories import UserFactory
from compliance.constants import (
    ActionPlanStatus,
    AssessmentStatus,
    ComplianceStatus,
    FindingType,
    FrameworkCategory,
    FrameworkType,
    MappingType,
    Priority,
    RequirementType,
)
from compliance.models.assessment import AssessmentResult, ComplianceAssessment
from compliance.models.finding import Finding
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
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Assessment {n}")
    assessor = factory.SubFactory(UserFactory)
    status = AssessmentStatus.DRAFT

    @factory.post_generation
    def framework(self, create, extracted, **kwargs):
        """Accept a single framework and add it to the M2M.

        Usage: ComplianceAssessmentFactory(framework=fw)
        """
        if not create:
            return
        if extracted:
            self.frameworks.add(extracted)

    @factory.post_generation
    def frameworks(self, create, extracted, **kwargs):
        """Accept a list of frameworks and add them to the M2M.

        Usage: ComplianceAssessmentFactory(frameworks=[fw1, fw2])
        """
        if not create:
            return
        if extracted:
            self.frameworks.add(*extracted)


class AssessmentResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssessmentResult

    assessment = factory.SubFactory(ComplianceAssessmentFactory)
    requirement = factory.SubFactory(RequirementFactory)
    compliance_status = ComplianceStatus.NOT_ASSESSED
    compliance_level = 0
    assessed_by = factory.SubFactory(UserFactory)
    assessed_at = factory.LazyFunction(timezone.now)


class FindingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Finding

    assessment = factory.SubFactory(ComplianceAssessmentFactory)
    finding_type = FindingType.MAJOR_NON_CONFORMITY
    description = factory.Sequence(lambda n: f"Finding description {n}")
    assessor = factory.SubFactory(UserFactory)


class MappingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RequirementMapping

    source_requirement = factory.SubFactory(RequirementFactory)
    target_requirement = factory.SubFactory(RequirementFactory)
    mapping_type = MappingType.EQUIVALENT


class ComplianceActionPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "compliance.ComplianceActionPlan"

    name = factory.Sequence(lambda n: f"Action Plan {n}")
    gap_description = "Test gap description"
    remediation_plan = "Test remediation plan"
    priority = Priority.MEDIUM
    owner = factory.SubFactory(UserFactory)
    target_date = factory.LazyFunction(
        lambda: (timezone.now() + timedelta(days=30)).date()
    )
    status = ActionPlanStatus.NOUVEAU


class ActionPlanCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "compliance.ActionPlanComment"

    action_plan = factory.SubFactory(ComplianceActionPlanFactory)
    author = factory.SubFactory(UserFactory)
    content = factory.Sequence(lambda n: f"Comment {n}")
    parent = None

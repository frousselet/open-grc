import factory

from accounts.tests.factories import UserFactory
from context.constants import (
    ImpactLevel,
    IssueCategory,
    IssueType,
    ObjectiveCategory,
    ObjectiveStatus,
    ObjectiveType,
)
from context.models.issue import Issue
from context.models.objective import Objective
from context.models.scope import Scope


class ScopeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scope

    name = factory.Sequence(lambda n: f"Scope {n}")
    description = "Test scope"


class IssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Issue

    scope = factory.SubFactory(ScopeFactory)
    name = factory.Sequence(lambda n: f"Issue {n}")
    type = IssueType.INTERNAL
    category = IssueCategory.STRATEGIC
    impact_level = ImpactLevel.MEDIUM


class ObjectiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Objective

    scope = factory.SubFactory(ScopeFactory)
    reference = factory.Sequence(lambda n: f"OBJ-{n:03d}")
    name = factory.Sequence(lambda n: f"Objective {n}")
    category = ObjectiveCategory.CONFIDENTIALITY
    type = ObjectiveType.SECURITY
    owner = factory.SubFactory(UserFactory)
    status = ObjectiveStatus.ACTIVE

import datetime

import factory

from accounts.tests.factories import UserFactory
from context.constants import (
    ImpactLevel,
    IssueCategory,
    IssueType,
    ObjectiveCategory,
    ObjectiveStatus,
    ObjectiveType,
    SwotQuadrant,
    SwotStatus,
)
from context.models.issue import Issue
from context.models.objective import Objective
from context.models.scope import Scope
from context.models.swot import SwotAnalysis, SwotItem


class ScopeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scope

    name = factory.Sequence(lambda n: f"Scope {n}")
    description = "Test scope"


class IssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Issue

    name = factory.Sequence(lambda n: f"Issue {n}")
    type = IssueType.INTERNAL
    category = IssueCategory.STRATEGIC
    impact_level = ImpactLevel.MEDIUM

    @factory.post_generation
    def scope(self, create, extracted, **kwargs):
        """Accept scope= for backwards compatibility, adds to scopes M2M."""
        if not create:
            return
        if extracted:
            self.scopes.add(extracted)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class SwotAnalysisFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SwotAnalysis

    name = factory.Sequence(lambda n: f"SWOT Analysis {n}")
    description = "Test SWOT analysis"
    analysis_date = factory.LazyFunction(datetime.date.today)
    status = SwotStatus.DRAFT

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class SwotItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SwotItem

    swot_analysis = factory.SubFactory(SwotAnalysisFactory)
    quadrant = SwotQuadrant.STRENGTH
    description = factory.Sequence(lambda n: f"SWOT item {n}")
    impact_level = ImpactLevel.MEDIUM


class ObjectiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Objective

    reference = factory.Sequence(lambda n: f"OBJ-{n:03d}")
    name = factory.Sequence(lambda n: f"Objective {n}")
    category = ObjectiveCategory.CONFIDENTIALITY
    type = ObjectiveType.SECURITY
    owner = factory.SubFactory(UserFactory)
    status = ObjectiveStatus.ACTIVE

    @factory.post_generation
    def scope(self, create, extracted, **kwargs):
        """Accept scope= for backwards compatibility, adds to scopes M2M."""
        if not create:
            return
        if extracted:
            self.scopes.add(extracted)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)

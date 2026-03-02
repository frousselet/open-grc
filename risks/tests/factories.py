import factory

from context.tests.factories import ScopeFactory
from risks.models.risk import Risk
from risks.models.risk_assessment import RiskAssessment
from risks.models.risk_criteria import RiskCriteria, RiskLevel, ScaleLevel


class RiskCriteriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskCriteria

    name = factory.Sequence(lambda n: f"Criteria {n}")
    status = "active"

    @factory.post_generation
    def scope(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.scopes.add(extracted)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class ScaleLevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScaleLevel

    criteria = factory.SubFactory(RiskCriteriaFactory)
    level = 1
    name = "Level"


class RiskLevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskLevel

    criteria = factory.SubFactory(RiskCriteriaFactory)
    level = 1
    name = "Low"
    color = "#4caf50"


class RiskAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskAssessment

    reference = factory.Sequence(lambda n: f"RA-{n:03d}")
    name = factory.Sequence(lambda n: f"Assessment {n}")

    @factory.post_generation
    def scope(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.scopes.add(extracted)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class RiskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Risk

    assessment = factory.SubFactory(RiskAssessmentFactory)
    reference = factory.Sequence(lambda n: f"RSK-{n:03d}")
    name = factory.Sequence(lambda n: f"Risk {n}")

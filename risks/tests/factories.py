import factory

from context.tests.factories import ScopeFactory
from risks.models.risk import Risk
from risks.models.risk_assessment import RiskAssessment
from risks.models.risk_criteria import RiskCriteria, RiskLevel, ScaleLevel


class RiskCriteriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskCriteria

    scope = factory.SubFactory(ScopeFactory)
    name = factory.Sequence(lambda n: f"Criteria {n}")
    status = "active"


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

    scope = factory.SubFactory(ScopeFactory)
    reference = factory.Sequence(lambda n: f"RA-{n:03d}")
    name = factory.Sequence(lambda n: f"Assessment {n}")


class RiskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Risk

    assessment = factory.SubFactory(RiskAssessmentFactory)
    reference = factory.Sequence(lambda n: f"RSK-{n:03d}")
    name = factory.Sequence(lambda n: f"Risk {n}")

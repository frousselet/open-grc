import pytest

from risks.tests.factories import (
    RiskAssessmentFactory,
    RiskCriteriaFactory,
    RiskFactory,
    RiskLevelFactory,
    ScaleLevelFactory,
)

pytestmark = pytest.mark.django_db


class TestRiskMatrixRebuild:
    """P0: rebuild_risk_matrix symmetric formula."""

    def _build_criteria_3x3(self):
        """Create a 3×3 criteria with 3 risk levels."""
        criteria = RiskCriteriaFactory()
        for i in range(1, 4):
            ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}")
            ScaleLevelFactory(criteria=criteria, scale_type="impact", level=i, name=f"I{i}")
        for i in range(1, 4):
            RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
        return criteria

    def test_matrix_populated(self):
        criteria = self._build_criteria_3x3()
        criteria.rebuild_risk_matrix()
        criteria.refresh_from_db()
        assert criteria.risk_matrix
        assert len(criteria.risk_matrix) == 9  # 3x3

    def test_matrix_symmetric(self):
        """cell(L,I) should equal cell(I,L)."""
        criteria = self._build_criteria_3x3()
        criteria.rebuild_risk_matrix()
        criteria.refresh_from_db()
        m = criteria.risk_matrix
        for l_val in range(1, 4):
            for i_val in range(1, 4):
                assert m[f"{l_val},{i_val}"] == m[f"{i_val},{l_val}"]

    def test_matrix_corners(self):
        """Low-low should map to lowest level, high-high to highest."""
        criteria = self._build_criteria_3x3()
        criteria.rebuild_risk_matrix()
        criteria.refresh_from_db()
        m = criteria.risk_matrix
        assert m["1,1"] == 1  # lowest
        assert m["3,3"] == 3  # highest

    def test_empty_scales_produces_empty_matrix(self):
        criteria = RiskCriteriaFactory()
        criteria.rebuild_risk_matrix()
        criteria.refresh_from_db()
        assert criteria.risk_matrix == {}


class TestRiskLevelCalculation:
    """P0: Risk.calculate_risk_level via matrix."""

    def _create_risk_with_criteria(self):
        criteria = RiskCriteriaFactory()
        for i in range(1, 4):
            ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}")
            ScaleLevelFactory(criteria=criteria, scale_type="impact", level=i, name=f"I{i}")
        for i in range(1, 4):
            RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
        criteria.rebuild_risk_matrix()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        return RiskFactory(assessment=assessment), criteria

    def test_auto_calculates_on_save(self):
        risk, criteria = self._create_risk_with_criteria()
        risk.current_likelihood = 3
        risk.current_impact = 3
        risk.save()
        risk.refresh_from_db()
        assert risk.current_risk_level is not None
        assert risk.current_risk_level == 3  # max in 3x3

    def test_initial_and_residual_calculated(self):
        risk, criteria = self._create_risk_with_criteria()
        risk.initial_likelihood = 1
        risk.initial_impact = 1
        risk.residual_likelihood = 2
        risk.residual_impact = 2
        risk.save()
        risk.refresh_from_db()
        assert risk.initial_risk_level == 1
        assert risk.residual_risk_level is not None

    def test_none_likelihood_returns_none(self):
        risk, criteria = self._create_risk_with_criteria()
        assert risk.calculate_risk_level(None, 3) is None

    def test_no_criteria_returns_none(self):
        assessment = RiskAssessmentFactory(risk_criteria=None)
        risk = RiskFactory(assessment=assessment)
        assert risk.calculate_risk_level(1, 1) is None

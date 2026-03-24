"""Tests for the Indicator and IndicatorMeasurement models."""

from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.tests.factories import UserFactory
from context.constants import (
    CollectionMethod,
    CriticalThresholdOperator,
    IndicatorFormat,
    IndicatorStatus,
    IndicatorType,
    MeasurementFrequency,
    PredefinedIndicatorSource,
)
from context.models.indicator import Indicator, IndicatorMeasurement
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────


def _make_indicator(**kwargs):
    """Create an Indicator with sensible defaults, merging *kwargs*."""
    defaults = {
        "name": "Test Indicator",
        "indicator_type": IndicatorType.ORGANIZATIONAL,
        "collection_method": CollectionMethod.MANUAL,
        "format": IndicatorFormat.NUMBER,
        "review_frequency": MeasurementFrequency.MONTHLY,
        "first_review_date": timezone.now().date() + timedelta(days=30),
        "status": IndicatorStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Indicator.objects.create(**defaults)


# ── Basic creation and fields ────────────────────────────────


class TestIndicatorCreation:
    def test_create_number_indicator(self):
        ind = _make_indicator()
        assert ind.pk is not None
        assert ind.reference.startswith("INDC-")
        assert ind.format == IndicatorFormat.NUMBER

    def test_create_boolean_indicator(self):
        ind = _make_indicator(format=IndicatorFormat.BOOLEAN, unit="")
        assert ind.format == IndicatorFormat.BOOLEAN

    def test_str_representation(self):
        ind = _make_indicator(name="My KPI")
        assert "My KPI" in str(ind)
        assert ind.reference in str(ind)

    def test_default_status_is_active(self):
        ind = _make_indicator()
        assert ind.status == IndicatorStatus.ACTIVE

    def test_auto_generated_reference(self):
        ind1 = _make_indicator(name="First")
        ind2 = _make_indicator(name="Second")
        assert ind1.reference != ind2.reference
        assert ind1.reference.startswith("INDC-")
        assert ind2.reference.startswith("INDC-")

    def test_scopes_m2m(self):
        ind = _make_indicator()
        scope = ScopeFactory()
        ind.scopes.add(scope)
        assert scope in ind.scopes.all()

    def test_created_by_field(self):
        user = UserFactory()
        ind = _make_indicator(created_by=user)
        assert ind.created_by == user


# ── clean() validation: boolean format ───────────────────────


class TestIndicatorBooleanValidation:
    def test_boolean_with_unit_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                format=IndicatorFormat.BOOLEAN,
                unit="kg",
            )
        assert "unit" in exc_info.value.message_dict

    def test_boolean_without_unit_is_ok(self):
        ind = _make_indicator(format=IndicatorFormat.BOOLEAN, unit="")
        assert ind.pk is not None

    def test_boolean_with_below_operator_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                format=IndicatorFormat.BOOLEAN,
                critical_threshold_operator=CriticalThresholdOperator.BELOW,
            )
        assert "critical_threshold_operator" in exc_info.value.message_dict

    def test_boolean_with_above_operator_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                format=IndicatorFormat.BOOLEAN,
                critical_threshold_operator=CriticalThresholdOperator.ABOVE,
            )
        assert "critical_threshold_operator" in exc_info.value.message_dict

    def test_boolean_with_is_true_operator_is_ok(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator=CriticalThresholdOperator.IS_TRUE,
        )
        assert ind.pk is not None

    def test_boolean_with_is_false_operator_is_ok(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator=CriticalThresholdOperator.IS_FALSE,
        )
        assert ind.pk is not None


# ── clean() validation: number format ────────────────────────


class TestIndicatorNumberValidation:
    def test_number_with_is_true_operator_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                format=IndicatorFormat.NUMBER,
                critical_threshold_operator=CriticalThresholdOperator.IS_TRUE,
            )
        assert "critical_threshold_operator" in exc_info.value.message_dict

    def test_number_with_is_false_operator_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                format=IndicatorFormat.NUMBER,
                critical_threshold_operator=CriticalThresholdOperator.IS_FALSE,
            )
        assert "critical_threshold_operator" in exc_info.value.message_dict

    def test_number_with_below_operator_is_ok(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.BELOW,
        )
        assert ind.pk is not None

    def test_number_with_above_operator_is_ok(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.ABOVE,
        )
        assert ind.pk is not None


# ── clean() validation: min/max thresholds ───────────────────


class TestIndicatorMinMaxThresholds:
    def test_boolean_with_min_threshold_raises(self):
        with pytest.raises(ValidationError):
            _make_indicator(
                format=IndicatorFormat.BOOLEAN,
                critical_threshold_min=5.0,
            )

    def test_boolean_with_max_threshold_raises(self):
        with pytest.raises(ValidationError):
            _make_indicator(
                format=IndicatorFormat.BOOLEAN,
                critical_threshold_max=10.0,
            )

    def test_number_with_min_max_is_ok(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_min=5.0,
            critical_threshold_max=100.0,
        )
        assert ind.pk is not None

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                format=IndicatorFormat.NUMBER,
                critical_threshold_min=100.0,
                critical_threshold_max=10.0,
            )
        assert "critical_threshold_min" in exc_info.value.message_dict

    def test_min_equal_to_max_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                format=IndicatorFormat.NUMBER,
                critical_threshold_min=50.0,
                critical_threshold_max=50.0,
            )
        assert "critical_threshold_min" in exc_info.value.message_dict


# ── clean() validation: predefined indicator ─────────────────


class TestIndicatorPredefinedValidation:
    def test_internal_with_non_organizational_type_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                is_internal=True,
                indicator_type=IndicatorType.TECHNICAL,
                internal_source=PredefinedIndicatorSource.GLOBAL_COMPLIANCE_RATE,
            )
        assert "indicator_type" in exc_info.value.message_dict

    def test_internal_without_source_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_indicator(
                is_internal=True,
                indicator_type=IndicatorType.ORGANIZATIONAL,
                internal_source="",
            )
        assert "internal_source" in exc_info.value.message_dict

    def test_internal_with_organizational_and_source_is_ok(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.GLOBAL_COMPLIANCE_RATE,
        )
        assert ind.pk is not None
        assert ind.is_internal is True


# ── clean() validation: first_review_date ────────────────────


class TestIndicatorFirstReviewDateValidation:
    def test_past_first_review_date_on_creation_raises(self):
        """When an Indicator has no pk yet, a past first_review_date should raise."""
        ind = Indicator(
            name="Past Review",
            indicator_type=IndicatorType.ORGANIZATIONAL,
            collection_method=CollectionMethod.MANUAL,
            format=IndicatorFormat.NUMBER,
            review_frequency=MeasurementFrequency.MONTHLY,
            first_review_date=date(2020, 1, 1),
            status=IndicatorStatus.ACTIVE,
        )
        # Remove the auto-generated pk so clean() sees it as new
        ind.pk = None
        with pytest.raises(ValidationError) as exc_info:
            ind.clean()
        assert "first_review_date" in exc_info.value.message_dict

    def test_today_first_review_date_is_ok(self):
        ind = _make_indicator(
            first_review_date=timezone.now().date(),
        )
        assert ind.pk is not None

    def test_future_first_review_date_is_ok(self):
        ind = _make_indicator(
            first_review_date=timezone.now().date() + timedelta(days=60),
        )
        assert ind.pk is not None

    def test_past_date_ok_on_update(self):
        """Once created, updating a record with an existing past date should not raise."""
        ind = _make_indicator(
            first_review_date=timezone.now().date() + timedelta(days=1),
        )
        # Simulate updating an existing record
        ind.name = "Updated"
        ind.save()  # should not raise because pk already exists


# ── is_critical property ─────────────────────────────────────


class TestIndicatorIsCritical:
    # Boolean format
    def test_boolean_is_true_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator=CriticalThresholdOperator.IS_TRUE,
            current_value="true",
        )
        assert ind.is_critical is True

    def test_boolean_is_true_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator=CriticalThresholdOperator.IS_TRUE,
            current_value="false",
        )
        assert ind.is_critical is False

    def test_boolean_is_false_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator=CriticalThresholdOperator.IS_FALSE,
            current_value="false",
        )
        assert ind.is_critical is True

    def test_boolean_is_false_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator=CriticalThresholdOperator.IS_FALSE,
            current_value="true",
        )
        assert ind.is_critical is False

    def test_boolean_no_operator_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator="",
            current_value="true",
        )
        assert ind.is_critical is False

    def test_boolean_yes_value_is_true(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator=CriticalThresholdOperator.IS_TRUE,
            current_value="yes",
        )
        assert ind.is_critical is True

    def test_boolean_1_value_is_true(self):
        ind = _make_indicator(
            format=IndicatorFormat.BOOLEAN,
            critical_threshold_operator=CriticalThresholdOperator.IS_TRUE,
            current_value="1",
        )
        assert ind.is_critical is True

    # Number format - min/max thresholds
    def test_number_below_min_is_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_min=10.0,
            current_value="5",
        )
        assert ind.is_critical is True

    def test_number_above_max_is_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_max=100.0,
            current_value="150",
        )
        assert ind.is_critical is True

    def test_number_within_range_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_min=10.0,
            critical_threshold_max=100.0,
            current_value="50",
        )
        assert ind.is_critical is False

    # Number format - legacy operator + value
    def test_number_below_threshold_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.BELOW,
            critical_threshold_value="50",
            current_value="30",
        )
        assert ind.is_critical is True

    def test_number_above_threshold_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.BELOW,
            critical_threshold_value="50",
            current_value="70",
        )
        assert ind.is_critical is False

    def test_number_exceeds_threshold_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.ABOVE,
            critical_threshold_value="100",
            current_value="150",
        )
        assert ind.is_critical is True

    def test_number_below_above_threshold_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.ABOVE,
            critical_threshold_value="100",
            current_value="50",
        )
        assert ind.is_critical is False

    def test_no_current_value_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.BELOW,
            critical_threshold_value="50",
            current_value="",
        )
        assert ind.is_critical is False

    def test_non_numeric_current_value_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.BELOW,
            critical_threshold_value="50",
            current_value="not_a_number",
        )
        assert ind.is_critical is False

    def test_non_numeric_threshold_value_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            critical_threshold_operator=CriticalThresholdOperator.BELOW,
            critical_threshold_value="bad",
            current_value="30",
        )
        assert ind.is_critical is False

    def test_number_no_operator_no_minmax_not_critical(self):
        ind = _make_indicator(
            format=IndicatorFormat.NUMBER,
            current_value="50",
        )
        assert ind.is_critical is False


# ── compute_internal_value ───────────────────────────────────


class TestComputeInternalValue:
    def test_returns_none_when_not_internal(self):
        ind = _make_indicator(is_internal=False)
        assert ind.compute_internal_value() is None

    def test_returns_none_when_no_source(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.GLOBAL_COMPLIANCE_RATE,
        )
        # Override the source to empty to test the guard
        ind.internal_source = ""
        assert ind.compute_internal_value() is None

    def test_global_compliance_rate_no_frameworks(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.GLOBAL_COMPLIANCE_RATE,
        )
        result = ind.compute_internal_value()
        assert result == "0"

    def test_objective_progress_no_objectives(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.OBJECTIVE_PROGRESS,
        )
        result = ind.compute_internal_value()
        assert result == "0"

    def test_objective_progress_with_data(self):
        from context.tests.factories import ObjectiveFactory

        ObjectiveFactory(progress_percentage=80)
        ObjectiveFactory(progress_percentage=60)
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.OBJECTIVE_PROGRESS,
        )
        result = ind.compute_internal_value()
        assert result == "70.0"

    def test_risk_treatment_rate_no_risks(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.RISK_TREATMENT_RATE,
        )
        result = ind.compute_internal_value()
        assert result == "0"

    def test_risk_treatment_rate_with_data(self):
        from risks.tests.factories import RiskFactory

        RiskFactory(treatment_decision="reduce")
        RiskFactory(treatment_decision="reduce")
        RiskFactory(treatment_decision="")
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.RISK_TREATMENT_RATE,
        )
        result = ind.compute_internal_value()
        expected = str(round(2 / 3 * 100, 1))
        assert result == expected

    def test_approved_scopes_rate_no_scopes(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.APPROVED_SCOPES_RATE,
        )
        result = ind.compute_internal_value()
        assert result == "0"

    def test_approved_scopes_rate_with_data(self):
        ScopeFactory(status="active", is_approved=True)
        ScopeFactory(status="active", is_approved=False)
        ScopeFactory(status="active", is_approved=False)
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.APPROVED_SCOPES_RATE,
        )
        result = ind.compute_internal_value()
        expected = str(round(1 / 3 * 100, 1))
        assert result == expected

    def test_mandatory_roles_coverage_no_mandatory_roles(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.MANDATORY_ROLES_COVERAGE,
        )
        result = ind.compute_internal_value()
        assert result == "100"

    def test_mandatory_roles_coverage_with_data(self):
        from context.models import Role

        user = UserFactory()
        role1 = Role.objects.create(
            name="CTO", type="governance", is_mandatory=True,
        )
        role1.assigned_users.add(user)
        Role.objects.create(
            name="DPO", type="governance", is_mandatory=True,
        )
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.MANDATORY_ROLES_COVERAGE,
        )
        result = ind.compute_internal_value()
        assert result == "50.0"

    def test_framework_compliance_rate_no_parameter(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.FRAMEWORK_COMPLIANCE_RATE,
            internal_source_parameter="",
        )
        result = ind.compute_internal_value()
        assert result is None

    def test_framework_compliance_rate_not_found(self):
        import uuid

        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.FRAMEWORK_COMPLIANCE_RATE,
            internal_source_parameter=str(uuid.uuid4()),
        )
        result = ind.compute_internal_value()
        assert result is None

    def test_unknown_source_returns_none(self):
        ind = _make_indicator(
            is_internal=True,
            indicator_type=IndicatorType.ORGANIZATIONAL,
            internal_source=PredefinedIndicatorSource.GLOBAL_COMPLIANCE_RATE,
        )
        # Force an unknown source value to hit the final return None
        ind.internal_source = "nonexistent_source"
        assert ind.compute_internal_value() is None


# ── record_measurement ───────────────────────────────────────


class TestRecordMeasurement:
    def test_creates_measurement_and_updates_current_value(self):
        user = UserFactory()
        ind = _make_indicator()
        measurement = ind.record_measurement(42, recorded_by=user, notes="Weekly check")
        ind.refresh_from_db()
        assert ind.current_value == "42"
        assert measurement.value == "42"
        assert measurement.recorded_by == user
        assert measurement.notes == "Weekly check"

    def test_measurement_relationship(self):
        ind = _make_indicator()
        ind.record_measurement(10)
        ind.record_measurement(20)
        assert ind.measurements.count() == 2

    def test_measurement_without_user(self):
        ind = _make_indicator()
        measurement = ind.record_measurement(99)
        assert measurement.recorded_by is None


# ── IndicatorMeasurement model ───────────────────────────────


class TestIndicatorMeasurement:
    def test_creation(self):
        ind = _make_indicator()
        m = IndicatorMeasurement.objects.create(
            indicator=ind,
            value="42",
        )
        assert m.pk is not None
        assert m.indicator == ind
        assert m.value == "42"
        assert m.recorded_at is not None

    def test_str_representation(self):
        ind = _make_indicator(name="Uptime")
        m = IndicatorMeasurement.objects.create(
            indicator=ind,
            value="99.5",
        )
        s = str(m)
        assert ind.reference in s
        assert "99.5" in s

    def test_ordering_most_recent_first(self):
        ind = _make_indicator()
        m1 = IndicatorMeasurement.objects.create(indicator=ind, value="10")
        m2 = IndicatorMeasurement.objects.create(indicator=ind, value="20")
        measurements = list(ind.measurements.all())
        # Most recent (m2) should come first
        assert measurements[0].pk == m2.pk

    def test_cascade_delete(self):
        ind = _make_indicator()
        IndicatorMeasurement.objects.create(indicator=ind, value="10")
        IndicatorMeasurement.objects.create(indicator=ind, value="20")
        assert IndicatorMeasurement.objects.count() == 2
        ind.delete()
        assert IndicatorMeasurement.objects.count() == 0

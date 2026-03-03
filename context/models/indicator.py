import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import (
    CollectionMethod,
    CriticalThresholdOperator,
    IndicatorFormat,
    IndicatorStatus,
    IndicatorType,
    PREDEFINED_SOURCE_FORMAT,
    PredefinedIndicatorSource,
    MeasurementFrequency,
)
from .base import ScopedModel


class Indicator(ScopedModel):
    REFERENCE_PREFIX = "INDC"

    name = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    indicator_type = models.CharField(
        _("Indicator type"),
        max_length=20,
        choices=IndicatorType.choices,
    )
    collection_method = models.CharField(
        _("Collection method"),
        max_length=20,
        choices=CollectionMethod.choices,
        default=CollectionMethod.MANUAL,
    )
    format = models.CharField(
        _("Format"),
        max_length=20,
        choices=IndicatorFormat.choices,
        default=IndicatorFormat.NUMBER,
    )
    unit = models.CharField(
        _("Unit"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("Applicable only for number format."),
    )
    current_value = models.CharField(
        _("Current value"),
        max_length=255,
        blank=True,
        default="",
    )
    expected_level = models.CharField(
        _("Expected level"),
        max_length=255,
        blank=True,
        default="",
    )
    critical_threshold_operator = models.CharField(
        _("Critical threshold"),
        max_length=20,
        choices=CriticalThresholdOperator.choices,
        blank=True,
        default="",
    )
    critical_threshold_value = models.CharField(
        _("Critical threshold value"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("For numbers only. For booleans, the operator defines the threshold."),
    )
    critical_threshold_min = models.FloatField(
        _("Minimum threshold"),
        null=True,
        blank=True,
        help_text=_("Critical if the value falls below this minimum (numbers only)."),
    )
    critical_threshold_max = models.FloatField(
        _("Maximum threshold"),
        null=True,
        blank=True,
        help_text=_("Critical if the value exceeds this maximum (numbers only)."),
    )
    review_frequency = models.CharField(
        _("Review frequency"),
        max_length=20,
        choices=MeasurementFrequency.choices,
    )
    first_review_date = models.DateField(
        _("First review date"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=IndicatorStatus.choices,
        default=IndicatorStatus.ACTIVE,
    )
    # Predefined Open GRC indicator fields
    is_internal = models.BooleanField(
        _("Predefined Open GRC indicator"),
        default=False,
    )
    internal_source = models.CharField(
        _("Predefined data source"),
        max_length=50,
        choices=PredefinedIndicatorSource.choices,
        blank=True,
        default="",
    )
    internal_source_parameter = models.CharField(
        _("Source parameter"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Optional parameter, e.g. framework ID for compliance rate by framework."),
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Indicator")
        verbose_name_plural = _("Indicators")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def clean(self):
        super().clean()
        # Boolean format cannot have a unit
        if self.format == IndicatorFormat.BOOLEAN and self.unit:
            raise ValidationError(
                {"unit": _("A boolean indicator cannot have a unit.")}
            )
        # Boolean threshold operators must be is_true or is_false
        if self.format == IndicatorFormat.BOOLEAN and self.critical_threshold_operator:
            if self.critical_threshold_operator not in (
                CriticalThresholdOperator.IS_TRUE,
                CriticalThresholdOperator.IS_FALSE,
            ):
                raise ValidationError(
                    {
                        "critical_threshold_operator": _(
                            "A boolean indicator must use 'Is true' or 'Is false' as threshold."
                        )
                    }
                )
        # Number threshold operators must be below or above
        if self.format == IndicatorFormat.NUMBER and self.critical_threshold_operator:
            if self.critical_threshold_operator not in (
                CriticalThresholdOperator.BELOW,
                CriticalThresholdOperator.ABOVE,
            ):
                raise ValidationError(
                    {
                        "critical_threshold_operator": _(
                            "A number indicator must use 'Falls below' or 'Exceeds' as threshold."
                        )
                    }
                )
        # Min/max thresholds only for numbers
        if self.format != IndicatorFormat.NUMBER:
            if self.critical_threshold_min is not None or self.critical_threshold_max is not None:
                raise ValidationError(
                    _("Min/max thresholds are only applicable to number indicators.")
                )
        # Min must be less than max when both are set
        if (
            self.critical_threshold_min is not None
            and self.critical_threshold_max is not None
            and self.critical_threshold_min >= self.critical_threshold_max
        ):
            raise ValidationError(
                {
                    "critical_threshold_min": _(
                        "The minimum threshold must be less than the maximum threshold."
                    )
                }
            )
        # Predefined indicators must be organizational
        if self.is_internal and self.indicator_type != IndicatorType.ORGANIZATIONAL:
            raise ValidationError(
                {
                    "indicator_type": _(
                        "Predefined Open GRC indicators must be of organizational type."
                    )
                }
            )
        # Predefined indicators must have a source
        if self.is_internal and not self.internal_source:
            raise ValidationError(
                {
                    "internal_source": _(
                        "A predefined indicator must have a data source."
                    )
                }
            )
        # First review date must be today or in the future (only on creation)
        if not self.pk and self.first_review_date:
            if self.first_review_date < timezone.now().date():
                raise ValidationError(
                    {
                        "first_review_date": _(
                            "The first review date must be today or in the future."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_critical(self):
        """Check if the current value breaches any critical threshold."""
        if not self.current_value:
            return False
        if self.format == IndicatorFormat.BOOLEAN:
            if not self.critical_threshold_operator:
                return False
            current_bool = self.current_value.lower() in ("true", "1", "yes")
            if self.critical_threshold_operator == CriticalThresholdOperator.IS_FALSE:
                return not current_bool
            if self.critical_threshold_operator == CriticalThresholdOperator.IS_TRUE:
                return current_bool
        elif self.format == IndicatorFormat.NUMBER:
            try:
                current = float(self.current_value)
            except (ValueError, TypeError):
                return False
            # Check min/max thresholds first
            if self.critical_threshold_min is not None and current < self.critical_threshold_min:
                return True
            if self.critical_threshold_max is not None and current > self.critical_threshold_max:
                return True
            # Fallback to legacy operator + value
            if self.critical_threshold_operator and self.critical_threshold_value:
                try:
                    threshold = float(self.critical_threshold_value)
                except (ValueError, TypeError):
                    return False
                if self.critical_threshold_operator == CriticalThresholdOperator.BELOW:
                    return current < threshold
                if self.critical_threshold_operator == CriticalThresholdOperator.ABOVE:
                    return current > threshold
        return False

    def compute_internal_value(self):
        """Compute the value from Open GRC internal data."""
        if not self.is_internal or not self.internal_source:
            return None

        source = self.internal_source

        if source == PredefinedIndicatorSource.GLOBAL_COMPLIANCE_RATE:
            return self._compute_global_compliance_rate()
        elif source == PredefinedIndicatorSource.FRAMEWORK_COMPLIANCE_RATE:
            return self._compute_framework_compliance_rate()
        elif source == PredefinedIndicatorSource.OBJECTIVE_PROGRESS:
            return self._compute_objective_progress()
        elif source == PredefinedIndicatorSource.RISK_TREATMENT_RATE:
            return self._compute_risk_treatment_rate()
        elif source == PredefinedIndicatorSource.APPROVED_SCOPES_RATE:
            return self._compute_approved_scopes_rate()
        elif source == PredefinedIndicatorSource.MANDATORY_ROLES_COVERAGE:
            return self._compute_mandatory_roles_coverage()
        return None

    def _compute_global_compliance_rate(self):
        from compliance.models import Framework
        frameworks = Framework.objects.all()
        if not frameworks.exists():
            return "0"
        total = 0
        count = 0
        for fw in frameworks:
            rate = fw.compliance_level
            if rate is not None:
                total += rate
                count += 1
        if count == 0:
            return "0"
        return str(round(total / count, 1))

    def _compute_framework_compliance_rate(self):
        if not self.internal_source_parameter:
            return None
        from compliance.models import Framework
        try:
            fw = Framework.objects.get(pk=self.internal_source_parameter)
            rate = fw.compliance_level
            return str(round(rate, 1)) if rate is not None else "0"
        except Framework.DoesNotExist:
            return None

    def _compute_objective_progress(self):
        from context.models import Objective
        objectives = Objective.objects.exclude(progress_percentage__isnull=True)
        if not objectives.exists():
            return "0"
        values = objectives.values_list("progress_percentage", flat=True)
        return str(round(sum(values) / len(values), 1))

    def _compute_risk_treatment_rate(self):
        from risks.models import Risk
        total = Risk.objects.count()
        if total == 0:
            return "0"
        treated = Risk.objects.exclude(treatment_decision="").exclude(
            treatment_decision__isnull=True
        ).count()
        return str(round(treated / total * 100, 1))

    def _compute_approved_scopes_rate(self):
        from context.models import Scope
        total = Scope.objects.exclude(status="archived").count()
        if total == 0:
            return "0"
        approved = Scope.objects.exclude(status="archived").filter(is_approved=True).count()
        return str(round(approved / total * 100, 1))

    def _compute_mandatory_roles_coverage(self):
        from django.db.models import Count
        from context.models import Role
        mandatory = Role.objects.filter(is_mandatory=True)
        total = mandatory.count()
        if total == 0:
            return "100"
        covered = mandatory.annotate(
            user_count=Count("assigned_users")
        ).filter(user_count__gt=0).count()
        return str(round(covered / total * 100, 1))

    def record_measurement(self, value, recorded_by=None, notes=""):
        """Record a new measurement for this indicator."""
        measurement = IndicatorMeasurement.objects.create(
            indicator=self,
            value=str(value),
            recorded_by=recorded_by,
            notes=notes,
        )
        self.current_value = str(value)
        self.save(update_fields=["current_value", "updated_at"])
        return measurement


class IndicatorMeasurement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        related_name="measurements",
        verbose_name=_("Indicator"),
    )
    value = models.CharField(_("Value"), max_length=255)
    recorded_at = models.DateTimeField(_("Recorded at"), auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="indicator_measurements",
        verbose_name=_("Recorded by"),
    )
    notes = models.TextField(_("Notes"), blank=True, default="")

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = _("Indicator measurement")
        verbose_name_plural = _("Indicator measurements")

    def __str__(self):
        return f"{self.indicator.reference} — {self.value} ({self.recorded_at:%Y-%m-%d})"

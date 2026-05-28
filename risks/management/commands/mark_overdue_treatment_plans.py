"""Flip in-flight treatment plans to OVERDUE once their target_date has passed.

Intended to be run daily by cron alongside expire_risk_acceptances.
Plans already in a terminal status (COMPLETED, CANCELLED) or already
marked OVERDUE are left untouched.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from risks.constants import TreatmentPlanStatus
from risks.models import RiskTreatmentPlan


TERMINAL_STATUSES = {
    TreatmentPlanStatus.COMPLETED,
    TreatmentPlanStatus.CANCELLED,
    TreatmentPlanStatus.OVERDUE,
}


class Command(BaseCommand):
    help = (
        "Set RiskTreatmentPlan.status to OVERDUE when target_date is past "
        "and the plan is not already completed, cancelled or overdue."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report changes that would be made without writing anything.",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        dry_run = options["dry_run"]

        candidates = (
            RiskTreatmentPlan.objects.filter(
                target_date__isnull=False,
                target_date__lt=today,
            )
            .exclude(status__in=TERMINAL_STATUSES)
            .select_related("risk", "owner")
            .order_by("target_date")
        )
        count = candidates.count()

        if count and not dry_run:
            # Use a loop (not .update()) so HistoricalRecords captures each
            # transition and any pre_save signals fire.
            for plan in candidates:
                plan.status = TreatmentPlanStatus.OVERDUE
                plan.save(update_fields=["status", "updated_at"])

        verb = "Would mark" if dry_run else "Marked"
        style = self.style.WARNING if count else self.style.SUCCESS
        self.stdout.write(style(f"{verb} {count} treatment plan(s) as OVERDUE."))

        if count:
            for plan in candidates:
                owner = (
                    getattr(plan.owner, "display_name", None)
                    or getattr(plan.owner, "email", None)
                    or "-"
                )
                risk_ref = plan.risk.reference if plan.risk_id else "-"
                self.stdout.write(
                    f"  - {plan.reference} (risk={risk_ref}) "
                    f"target {plan.target_date.isoformat()} - owner={owner}"
                )

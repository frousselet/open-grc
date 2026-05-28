"""Expire risk acceptances past their valid_until date.

Designed to be run daily by cron. The companion `--reminder-days`
flag lists acceptances that will expire within the configured window
so operators can be reminded ahead of time.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from risks.constants import AcceptanceStatus
from risks.models import RiskAcceptance


class Command(BaseCommand):
    help = (
        "Set RiskAcceptance.status to EXPIRED for any active acceptance whose "
        "valid_until date has passed; print upcoming expirations within "
        "--reminder-days (default 30)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reminder-days",
            type=int,
            default=30,
            help="Window in days for the upcoming-expirations reminder list (default: 30).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report changes that would be made without writing anything.",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        reminder_days = options["reminder_days"]
        dry_run = options["dry_run"]

        to_expire = RiskAcceptance.objects.filter(
            status=AcceptanceStatus.ACTIVE,
            valid_until__isnull=False,
            valid_until__lt=today,
        )
        expired_count = to_expire.count()
        if expired_count and not dry_run:
            to_expire.update(status=AcceptanceStatus.EXPIRED)

        verb = "Would expire" if dry_run else "Expired"
        style = self.style.WARNING if expired_count else self.style.SUCCESS
        self.stdout.write(style(f"{verb} {expired_count} acceptance(s)."))

        if reminder_days > 0:
            upcoming = (
                RiskAcceptance.objects.filter(
                    status=AcceptanceStatus.ACTIVE,
                    valid_until__isnull=False,
                    valid_until__gte=today,
                    valid_until__lte=today + timedelta(days=reminder_days),
                )
                .select_related("risk", "accepted_by")
                .order_by("valid_until")
            )
            if upcoming.exists():
                self.stdout.write(
                    f"Upcoming expirations within {reminder_days} day(s):"
                )
                for acc in upcoming:
                    accepted_by = (
                        getattr(acc.accepted_by, "display_name", None)
                        or getattr(acc.accepted_by, "email", None)
                        or "-"
                    )
                    risk_ref = acc.risk.reference if acc.risk_id else "-"
                    self.stdout.write(
                        f"  - {acc.reference} (risk={risk_ref}) "
                        f"expires on {acc.valid_until.isoformat()} - "
                        f"accepted_by={accepted_by}"
                    )
            else:
                self.stdout.write("No upcoming expirations.")

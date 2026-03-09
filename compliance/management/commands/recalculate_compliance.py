from django.core.management.base import BaseCommand

from compliance.models import ComplianceAssessment


class Command(BaseCommand):
    help = "Recalculate compliance counts for all assessments, then propagate to requirements/sections/frameworks."

    def handle(self, *args, **options):
        assessments = ComplianceAssessment.objects.select_related("framework").all()
        count = assessments.count()
        for i, assessment in enumerate(assessments, 1):
            assessment.recalculate_counts()
            self.stdout.write(f"  [{i}/{count}] {assessment}")
        self.stdout.write(self.style.SUCCESS(f"Recalculated {count} assessment(s)."))

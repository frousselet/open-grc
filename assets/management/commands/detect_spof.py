from django.core.management.base import BaseCommand

from assets.services.spof_detection import SpofDetector
from context.models import Scope


class Command(BaseCommand):
    help = "Detect Single Points of Failure (SPOF) in the dependency graph"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply detected SPOF flags to the database (default: dry-run)",
        )
        parser.add_argument(
            "--scope",
            type=str,
            default=None,
            help="Filter analysis to a specific scope (by name)",
        )

    def handle(self, *args, **options):
        scope = None
        if options["scope"]:
            try:
                scope = Scope.objects.get(name=options["scope"])
            except Scope.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Scope '{options['scope']}' not found."))
                return

        detector = SpofDetector(scope=scope)

        if options["apply"]:
            results = detector.apply()
            self.stdout.write(self.style.SUCCESS(
                f"SPOF detection applied: "
                f"{results['total_spof']} SPOF detected, "
                f"{results['total_changed']} changes made."
            ))
            for key in ["asset_dependencies", "supplier_dependencies",
                        "site_asset_dependencies", "site_supplier_dependencies"]:
                info = results[key]
                self.stdout.write(
                    f"  {key}: {info['spof_count']}/{info['total']} SPOF "
                    f"({info['changed']} changed)"
                )
        else:
            results = detector.detect_all()
            self.stdout.write(self.style.WARNING("Dry-run (use --apply to update database)"))
            self.stdout.write(f"Total SPOF detected: {results['total_spof']}")
            for key in ["asset_dependencies", "supplier_dependencies",
                        "site_asset_dependencies", "site_supplier_dependencies"]:
                deps = results[key]
                spof_deps = [d for d in deps if d["is_spof"]]
                self.stdout.write(f"\n  {key}: {len(spof_deps)}/{len(deps)} SPOF")
                for dep in spof_deps:
                    self.stdout.write(
                        f"    - {dep['label']} [{', '.join(dep['rules'])}]"
                    )

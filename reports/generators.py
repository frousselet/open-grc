"""PDF report generators."""

import re

from django.template.loader import render_to_string
from django.utils import timezone


def _natural_sort_key(text):
    """Return a sort key that orders numeric parts numerically."""
    parts = re.split(r"(\d+)", text)
    return [int(p) if p.isdigit() else p.casefold() for p in parts]


def generate_soa_pdf(frameworks, user):
    """Generate a Statement of Applicability (SoA) PDF for the given frameworks.

    Returns a tuple (filename, content_bytes).
    """
    from weasyprint import HTML

    frameworks_data = []
    for fw in frameworks:
        requirements = fw.requirements.select_related(
            "section",
        ).prefetch_related(
            "linked_risks",
            "action_plans",
        ).order_by("requirement_number", "created_at")

        rows = []
        for req in requirements:
            risks = req.linked_risks.all()
            risk_names = ", ".join(r.name for r in risks) if risks else ""
            if req.is_applicable:
                plans = req.action_plans.all()
                justification = ", ".join(p.name for p in plans) if plans else ""
            else:
                justification = req.applicability_justification
            rows.append({
                "number": req.requirement_number or req.reference,
                "name": req.name,
                "is_applicable": req.is_applicable,
                "justification": justification,
                "risks": risk_names,
            })

        rows.sort(key=lambda r: _natural_sort_key(r["number"]))

        frameworks_data.append({
            "framework": fw,
            "rows": rows,
        })

    now = timezone.now()
    html_string = render_to_string("reports/soa_pdf.html", {
        "frameworks_data": frameworks_data,
        "generated_at": now,
        "generated_by": user,
    })

    pdf_bytes = HTML(string=html_string).write_pdf()

    date_str = now.strftime("%Y%m%d_%H%M%S")
    filename = f"SoA_{date_str}.pdf"

    return filename, pdf_bytes

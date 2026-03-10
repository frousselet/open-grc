"""PDF report generators."""

import io

from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML


def generate_soa_pdf(frameworks, user):
    """Generate a Statement of Applicability (SoA) PDF for the given frameworks.

    Returns a tuple (filename, content_bytes).
    """
    frameworks_data = []
    for fw in frameworks:
        requirements = fw.requirements.select_related(
            "section",
        ).prefetch_related(
            "linked_risks",
        ).order_by("requirement_number", "created_at")

        rows = []
        for req in requirements:
            risks = req.linked_risks.all()
            risk_names = ", ".join(r.name for r in risks) if risks else ""
            rows.append({
                "number": req.requirement_number or req.reference,
                "name": req.name,
                "is_applicable": req.is_applicable,
                "justification": req.applicability_justification,
                "risks": risk_names,
            })

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

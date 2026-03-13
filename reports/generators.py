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


def generate_audit_report_pdf(assessment, user):
    """Generate an Audit Report PDF for a completed compliance assessment.

    Returns a tuple (filename, content_bytes).
    """
    from weasyprint import HTML

    from compliance.constants import ComplianceStatus, FindingType

    # Gather results grouped by framework
    frameworks = assessment.frameworks.all()
    results = (
        assessment.results
        .select_related("requirement__section", "requirement__framework", "assessed_by")
        .order_by("requirement__framework__name", "requirement__requirement_number")
    )

    frameworks_data = []
    for fw in frameworks:
        fw_results = [r for r in results if r.requirement.framework_id == fw.pk]
        rows = []
        for r in fw_results:
            rows.append({
                "number": r.requirement.requirement_number or r.requirement.reference,
                "name": r.requirement.name,
                "status": r.get_compliance_status_display(),
                "status_key": r.compliance_status,
                "compliance_level": r.compliance_level,
                "finding": r.finding,
                "evidence": r.evidence,
            })
        rows.sort(key=lambda row: _natural_sort_key(row["number"]))
        frameworks_data.append({
            "framework": fw,
            "rows": rows,
        })

    # Gather findings
    findings = (
        assessment.findings
        .prefetch_related("requirements")
        .select_related("assessor")
        .order_by("reference")
    )
    findings_data = []
    for f in findings:
        req_refs = ", ".join(
            r.requirement_number or r.reference for r in f.requirements.all()
        )
        findings_data.append({
            "reference": f.reference,
            "type_display": f.get_finding_type_display(),
            "finding_type": f.finding_type,
            "description": f.description,
            "recommendation": f.recommendation,
            "evidence": f.evidence,
            "requirements": req_refs,
        })

    # Summary statistics
    summary = {
        "total": assessment.total_requirements,
        "compliant": assessment.compliant_count,
        "major_nc": assessment.major_non_conformity_count,
        "minor_nc": assessment.minor_non_conformity_count,
        "observation": assessment.observation_count,
        "improvement": assessment.improvement_opportunity_count,
        "strength": assessment.strength_count,
        "not_assessed": assessment.not_assessed_count,
        "not_applicable": assessment.not_applicable_count,
        "overall_compliance": assessment.overall_compliance_level,
        "coverage_pct": assessment.coverage_pct,
        "compliance_pct": assessment.compliance_pct,
    }

    now = timezone.now()
    html_string = render_to_string("reports/audit_report_pdf.html", {
        "assessment": assessment,
        "frameworks_data": frameworks_data,
        "findings_data": findings_data,
        "summary": summary,
        "generated_at": now,
        "generated_by": user,
        "ComplianceStatus": ComplianceStatus,
        "FindingType": FindingType,
    })

    pdf_bytes = HTML(string=html_string).write_pdf()

    date_str = now.strftime("%Y%m%d_%H%M%S")
    filename = f"Audit_Report_{assessment.reference}_{date_str}.pdf"

    return filename, pdf_bytes

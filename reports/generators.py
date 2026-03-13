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


def _build_scope_tree(scopes):
    """Build a tree structure from a flat list of scopes.

    Returns a list of dicts: {scope, depth, children} ordered depth-first.
    Each scope in the input is placed under its parent if the parent is also
    in the list; otherwise it becomes a root node.
    """
    scope_ids = {s.pk for s in scopes}
    scope_map = {s.pk: s for s in scopes}

    # Build children mapping
    children_map = {}  # parent_pk -> [child scopes]
    roots = []
    for s in scopes:
        parent_pk = s.parent_scope_id
        if parent_pk and parent_pk in scope_ids:
            children_map.setdefault(parent_pk, []).append(s)
        else:
            roots.append(s)

    # Sort roots and children by name
    roots.sort(key=lambda s: s.name)
    for k in children_map:
        children_map[k].sort(key=lambda s: s.name)

    # Flatten depth-first
    result = []

    def _walk(scope, depth):
        result.append({"scope": scope, "depth": depth})
        for child in children_map.get(scope.pk, []):
            _walk(child, depth + 1)

    for root in roots:
        _walk(root, 0)

    return result


def _compliance_color(status_key):
    """Return a CSS row color class for a compliance status."""
    if status_key in ("compliant", "strength"):
        return "row-compliant"
    if status_key in ("minor_non_conformity", "observation", "improvement_opportunity"):
        return "row-partial"
    if status_key == "major_non_conformity":
        return "row-non-compliant"
    if status_key == "not_applicable":
        return "row-na"
    return ""


def _finding_color(finding_type):
    """Return a CSS row color class for a finding type."""
    if finding_type == "strength":
        return "row-compliant"
    if finding_type in ("minor_nc", "observation", "improvement"):
        return "row-partial"
    if finding_type == "major_nc":
        return "row-non-compliant"
    return ""


def generate_audit_report_pdf(assessment, user):
    """Generate an Audit Report PDF for a completed compliance assessment.

    Returns a tuple (filename, content_bytes).
    """
    from weasyprint import HTML

    from compliance.constants import ComplianceStatus, FindingType

    # Gather results grouped by framework
    frameworks = list(assessment.frameworks.all())
    scopes = list(assessment.scopes.select_related("parent_scope"))
    scope_tree = _build_scope_tree(scopes)
    results = list(
        assessment.results
        .select_related("requirement__section", "requirement__framework", "assessed_by")
        .order_by("requirement__framework__name", "requirement__requirement_number")
    )

    # Build findings data
    findings = list(
        assessment.findings
        .prefetch_related("requirements")
        .select_related("assessor")
        .order_by("reference")
    )

    # Build requirement_id → finding mapping for per-framework finding cards
    req_id_to_findings = {}
    for f in findings:
        for req in f.requirements.all():
            req_id_to_findings.setdefault(req.pk, []).append(f)

    # Build findings recap (section 2.2)
    findings_recap = []
    for f in findings:
        reqs = list(f.requirements.all())
        req_display = ", ".join(
            r.requirement_number or r.reference for r in reqs
        )
        req_names = "; ".join(r.name for r in reqs)
        findings_recap.append({
            "reference": f.reference,
            "requirement_refs": req_display,
            "requirement_names": req_names,
            "type_display": f.get_finding_type_display(),
            "finding_type": f.finding_type,
            "color": _finding_color(f.finding_type),
        })

    # Build frameworks data
    frameworks_data = []
    for idx, fw in enumerate(frameworks):
        fw_results = [r for r in results if r.requirement.framework_id == fw.pk]

        # Compliance state rows (section X.1)
        compliance_rows = []
        for r in fw_results:
            compliance_rows.append({
                "number": r.requirement.requirement_number or r.requirement.reference,
                "name": r.requirement.name,
                "status": r.get_compliance_status_display(),
                "status_key": r.compliance_status,
                "color": _compliance_color(r.compliance_status),
            })
        compliance_rows.sort(key=lambda row: _natural_sort_key(row["number"]))

        # Findings detail cards for this framework (section X.2)
        fw_req_ids = {r.requirement.pk for r in fw_results}
        fw_findings = []
        seen_finding_ids = set()
        for f in findings:
            if f.pk in seen_finding_ids:
                continue
            f_req_ids = {r.pk for r in f.requirements.all()}
            if f_req_ids & fw_req_ids:
                seen_finding_ids.add(f.pk)
                reqs = [r for r in f.requirements.all() if r.pk in fw_req_ids]
                req_display = ", ".join(
                    r.requirement_number or r.reference for r in reqs
                )
                req_detail = "\n".join(
                    f"{r.requirement_number or r.reference} — {r.name}" for r in reqs
                )
                fw_findings.append({
                    "reference": f.reference,
                    "type_display": f.get_finding_type_display(),
                    "finding_type": f.finding_type,
                    "color": _finding_color(f.finding_type),
                    "requirement_refs": req_display,
                    "requirement_detail": req_detail,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "evidence": f.evidence,
                })

        frameworks_data.append({
            "framework": fw,
            "section_num": idx + 3,
            "compliance_rows": compliance_rows,
            "findings": fw_findings,
        })

    # Summary statistics
    from collections import Counter
    finding_type_counts = Counter(f.finding_type for f in findings)
    summary = {
        "total": assessment.total_requirements,
        "overall_compliance": assessment.overall_compliance_level,
        "coverage_pct": assessment.coverage_pct,
        "total_findings": len(findings),
    }
    findings_by_type = [
        {
            "label": FindingType.MAJOR_NON_CONFORMITY.label,
            "count": finding_type_counts.get("major_nc", 0),
            "color": "row-non-compliant",
        },
        {
            "label": FindingType.MINOR_NON_CONFORMITY.label,
            "count": finding_type_counts.get("minor_nc", 0),
            "color": "row-partial",
        },
        {
            "label": FindingType.OBSERVATION.label,
            "count": finding_type_counts.get("observation", 0),
            "color": "row-partial",
        },
        {
            "label": FindingType.IMPROVEMENT_OPPORTUNITY.label,
            "count": finding_type_counts.get("improvement", 0),
            "color": "row-partial",
        },
        {
            "label": FindingType.STRENGTH.label,
            "count": finding_type_counts.get("strength", 0),
            "color": "row-compliant",
        },
    ]

    # Finding type definitions for section 1.4
    finding_qualifications = [
        {
            "type": FindingType.MAJOR_NON_CONFORMITY.label,
            "color": "row-non-compliant",
        },
        {
            "type": FindingType.MINOR_NON_CONFORMITY.label,
            "color": "row-partial",
        },
        {
            "type": FindingType.OBSERVATION.label,
            "color": "row-partial",
        },
        {
            "type": FindingType.IMPROVEMENT_OPPORTUNITY.label,
            "color": "row-partial",
        },
        {
            "type": FindingType.STRENGTH.label,
            "color": "row-compliant",
        },
    ]

    now = timezone.now()
    html_string = render_to_string("reports/audit_report_pdf.html", {
        "assessment": assessment,
        "scope_tree": scope_tree,
        "frameworks": frameworks,
        "frameworks_data": frameworks_data,
        "findings_recap": findings_recap,
        "summary": summary,
        "findings_by_type": findings_by_type,
        "finding_qualifications": finding_qualifications,
        "generated_at": now,
        "generated_by": user,
    })

    pdf_bytes = HTML(string=html_string).write_pdf()

    date_str = now.strftime("%Y%m%d_%H%M%S")
    filename = f"Audit_Report_{assessment.reference}_{date_str}.pdf"

    return filename, pdf_bytes

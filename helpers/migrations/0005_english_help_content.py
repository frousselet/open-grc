from django.db import migrations


HELP_CONTENT_EN = [
    # ── Home ──────────────────────────────────────────────────
    {
        "key": "home",
        "title": "General dashboard",
        "body": (
            "The dashboard provides a consolidated overview of the entire GRC "
            "framework: governance, asset management, compliance and risk management. "
            "Key performance indicators (KPIs) and charts let you monitor progress "
            "across all modules in real time and quickly spot areas that need attention."
        ),
    },
    # ── Context ──────────────────────────────────────────────
    {
        "key": "context.dashboard",
        "title": "Governance",
        "body": (
            "This module forms the foundation of the GRC framework. It lets you "
            "define the management system scope, identify internal and external issues, "
            "list interested parties and their expectations, set objectives, perform "
            "SWOT analyses, assign roles and responsibilities, and map business "
            "activities. Aligned with clauses 4 and 5 of the ISO Harmonized Structure "
            "(applicable to ISO 27001, 9001, 14001, 22301, 45001, etc.)."
        ),
    },
    {
        "key": "context.scope_list",
        "title": "Scopes",
        "body": (
            "The scope defines the boundaries of the management system "
            "(ISO Harmonized Structure §4.3). It specifies the organisational, "
            "geographical and technical perimeters covered, as well as justified "
            "exclusions. Only one scope can be active at a time; previous versions "
            "are automatically archived."
        ),
    },
    {
        "key": "context.issue_list",
        "title": "Issues",
        "body": (
            "Issues are the internal and external factors that can affect the "
            "organisation's ability to achieve the intended outcomes of its management "
            "system (ISO Harmonized Structure §4.1). Internal issues cover strategy, "
            "organisation, human resources, technology and culture. External issues "
            "cover political, economic, social, technological, legal and environmental "
            "aspects."
        ),
    },
    {
        "key": "context.stakeholder_list",
        "title": "Stakeholders",
        "body": (
            "Stakeholders are individuals or organisations that can affect, be affected "
            "by, or perceive themselves to be affected by the organisation's decisions "
            "(ISO Harmonized Structure §4.2). For each stakeholder, you assess their "
            "level of influence and interest, and record their expectations and "
            "requirements regarding the management system."
        ),
    },
    {
        "key": "context.objective_list",
        "title": "Objectives",
        "body": (
            "Management system objectives must be measurable and consistent with the "
            "organisation's policy (ISO Harmonized Structure §6.2). Each objective "
            "is linked to a scope, assigned to a responsible party, and tracked "
            "through a completion percentage. Objectives can be hierarchised "
            "(parent/child) and linked to issues and stakeholders."
        ),
    },
    {
        "key": "context.swot_list",
        "title": "SWOT analyses",
        "body": (
            "The SWOT analysis identifies Strengths, Weaknesses, Opportunities and "
            "Threats of the GRC framework. Each item is ranked by impact and can be "
            "linked to identified issues and objectives. The SWOT analysis provides "
            "a summarised view to guide the organisation's strategy."
        ),
    },
    {
        "key": "context.role_list",
        "title": "Roles and responsibilities",
        "body": (
            "Roles define the functions and responsibilities within the organisation's "
            "management system (ISO Harmonized Structure §5.3). Each role can be "
            "strategic, operational or technical, and its responsibilities are "
            "documented through a RACI matrix. Mandatory roles that are unassigned "
            "trigger an alert."
        ),
    },
    {
        "key": "context.activity_list",
        "title": "Activities and processes",
        "body": (
            "Activities and processes represent the business and technical functions "
            "of the organisation that fall within the management system scope. Each "
            "activity is characterised by its type (business, support, management), "
            "its criticality and its owner. They serve as the basis for asset "
            "identification and risk and opportunity analysis."
        ),
    },
    {
        "key": "context.site_list",
        "title": "Sites",
        "body": (
            "Sites represent the organisation's geographical locations (headquarters, "
            "branches, data centres, industrial sites, etc.). Each site is "
            "characterised by its address, type and criticality. Sites serve as a "
            "reference for locating support assets and analysing risks related to "
            "physical and environmental threats."
        ),
    },
    # ── Assets ───────────────────────────────────────────────
    {
        "key": "assets.dashboard",
        "title": "Asset management",
        "body": (
            "The asset management module lets you inventory essential assets "
            "(processes, information) and support assets (hardware, software, network, "
            "sites, people) of the organisation. CIA valuation levels (Confidentiality, "
            "Integrity, Availability) are automatically inherited from essential assets "
            "to support assets through dependency relationships. This module supports "
            "the asset identification process required by applicable frameworks "
            "(ISO 27001, EBIOS RM, etc.)."
        ),
    },
    {
        "key": "assets.essential_asset_list",
        "title": "Essential assets",
        "body": (
            "Essential assets are the business processes and information that hold "
            "value for the organisation and require protection. Each essential asset "
            "is assessed against CIA criteria (Confidentiality, Integrity, "
            "Availability) on a scale from 0 to 4. These levels are propagated "
            "to associated support assets through dependency relationships."
        ),
    },
    {
        "key": "assets.support_asset_list",
        "title": "Support assets",
        "body": (
            "Support assets are the information system components on which essential "
            "assets rely: hardware, software, network, people, sites and services. "
            "Their CIA levels are automatically inherited from linked essential assets "
            "(MAX algorithm). End-of-life or orphaned assets (with no linked essential "
            "asset) are flagged with an alert."
        ),
    },
    {
        "key": "assets.dependency_list",
        "title": "Dependency relationships",
        "body": (
            "Dependency relationships link essential assets to the support assets "
            "that carry them. Each dependency is characterised by its type (hosting, "
            "processing, access, transport), its criticality and its level of "
            "redundancy. Single points of failure (SPOF) — critical support assets "
            "with no redundancy — are automatically detected and flagged."
        ),
    },
    {
        "key": "assets.group_list",
        "title": "Asset groups",
        "body": (
            "Asset groups let you cluster support assets that share common "
            "characteristics (same location, same function, same technology) to "
            "simplify management and risk analysis. A group can be logical, "
            "geographical, functional or technological."
        ),
    },
    # ── Accounts ─────────────────────────────────────────────
    {
        "key": "accounts.user_list",
        "title": "Users",
        "body": (
            "User management lets you create, edit and deactivate platform user "
            "accounts. Each user is identified by their email address and can be "
            "assigned to one or more groups that determine their access rights."
        ),
    },
    {
        "key": "accounts.group_list",
        "title": "Permission groups",
        "body": (
            "Groups let you assign sets of permissions to users. System groups are "
            "created during installation and cannot be modified. Custom groups can "
            "be created to meet the organisation's specific needs."
        ),
    },
    {
        "key": "accounts.permission_list",
        "title": "Permissions",
        "body": (
            "Permissions control granular access to platform features. Each "
            "permission follows the module.feature.action format and is assigned "
            "exclusively through groups."
        ),
    },
    {
        "key": "accounts.access_log_list",
        "title": "Access log",
        "body": (
            "The access log records all authentication events: successful and failed "
            "logins, logouts, account lockouts and password changes. It enables "
            "traceability and detection of security anomalies."
        ),
    },
    {
        "key": "accounts.action_log_list",
        "title": "Action log",
        "body": (
            "The action log traces all operations performed by users on the platform: "
            "creations, updates, deletions and approvals. It ensures full traceability "
            "of changes and meets audit requirements."
        ),
    },
    # ── Compliance ───────────────────────────────────────────
    {
        "key": "compliance.dashboard",
        "title": "Compliance management",
        "body": (
            "The compliance module lets you manage the regulatory and normative "
            "frameworks applicable to the organisation, assess the level of compliance "
            "against each requirement, and steer remediation action plans. It covers "
            "the full cycle: framework import, assessment, gap mapping and remediation "
            "tracking."
        ),
    },
    {
        "key": "compliance.framework_list",
        "title": "Frameworks",
        "body": (
            "Frameworks group the standards, regulations and best-practice guides "
            "applicable to the organisation (ISO 27001, GDPR, NIS 2, etc.). Each "
            "framework is structured into hierarchical sections containing "
            "requirements. Frameworks can be imported from JSON or Excel files, "
            "and their applicability can be adjusted per scope."
        ),
    },
    {
        "key": "compliance.requirement_list",
        "title": "Requirements",
        "body": (
            "Requirements are the individual obligations drawn from applicable "
            "frameworks. Each requirement belongs to a framework section and can be "
            "mandatory, recommended or optional. Requirements serve as the basis for "
            "compliance assessments and action plans."
        ),
    },
    {
        "key": "compliance.assessment_list",
        "title": "Compliance assessments",
        "body": (
            "Compliance assessments measure the organisation's level of compliance "
            "against a given framework within a defined scope. Each assessment "
            "produces per-requirement results (compliant, partially compliant, "
            "non-compliant, not applicable) and identifies the gaps to be addressed."
        ),
    },
    {
        "key": "compliance.mapping_list",
        "title": "Cross-framework mappings",
        "body": (
            "Cross-framework mappings establish correspondences between the "
            "requirements of different frameworks. They help identify overlaps, "
            "optimise compliance efforts and demonstrate how satisfying one "
            "requirement contributes to compliance with other frameworks "
            "(e.g. ISO 27001 → GDPR, NIS 2 → ISO 27001)."
        ),
    },
    {
        "key": "compliance.action_plan_list",
        "title": "Compliance action plans",
        "body": (
            "Compliance action plans formalise the corrective and preventive actions "
            "needed to close the gaps identified during assessments. Each action plan "
            "is linked to an assessment and a requirement, with an owner, a priority, "
            "target dates and progress tracking."
        ),
    },
    {
        "key": "compliance.framework_import",
        "title": "Framework import",
        "body": (
            "The import feature lets you load a complete framework with its full "
            "hierarchy (sections and requirements) from a JSON or Excel file. The "
            "file is parsed and a preview is shown before confirmation. You can "
            "import into an existing framework to add new sections and requirements."
        ),
    },
    # ── Risks ────────────────────────────────────────────────
    {
        "key": "risks.dashboard",
        "title": "Risk management",
        "body": (
            "The risk management module covers the entire risk assessment and "
            "treatment process in line with ISO 27005 and ISO 31000. It lets you "
            "identify, analyse and evaluate risks, define treatment plans, and track "
            "residual risk acceptances. Dashboards provide a consolidated view of "
            "the organisation's risk posture."
        ),
    },
    {
        "key": "risks.risk_list",
        "title": "Risk register",
        "body": (
            "The risk register centralises all risks identified for the organisation. "
            "Each risk is characterised by its source, consequences, likelihood and "
            "impact, enabling calculation of inherent and residual risk levels. Risks "
            "can be linked to identified assets, threats and vulnerabilities."
        ),
    },
    {
        "key": "risks.assessment_list",
        "title": "Risk assessments",
        "body": (
            "Risk assessments formalise the process of identifying, analysing and "
            "evaluating risks within a given scope. Each assessment follows a defined "
            "methodology (ISO 27005, EBIOS RM, etc.) and produces a list of evaluated "
            "risks with their levels."
        ),
    },
    {
        "key": "risks.criteria_list",
        "title": "Risk criteria",
        "body": (
            "Risk criteria define the scales and thresholds used for risk evaluation: "
            "likelihood scale, impact scale, risk matrix and acceptability thresholds. "
            "They ensure consistency and reproducibility of risk assessments."
        ),
    },
    {
        "key": "risks.treatment_plan_list",
        "title": "Treatment plans",
        "body": (
            "Treatment plans define the measures to be implemented to bring risks "
            "down to an acceptable level. Treatment options include reduction "
            "(implementing controls), transfer (insurance, outsourcing), avoidance "
            "(removing the activity) and acceptance (validated residual risk)."
        ),
    },
    {
        "key": "risks.acceptance_list",
        "title": "Risk acceptances",
        "body": (
            "Risk acceptances formalise management's decision to accept a residual "
            "risk after treatment. Each acceptance is documented with its "
            "justification, validity period and responsible signatory. Expired or "
            "due-for-renewal acceptances are flagged automatically."
        ),
    },
    {
        "key": "risks.threat_list",
        "title": "Threats",
        "body": (
            "Threats represent potential causes of incidents that could harm the "
            "organisation's assets. They are classified by type (natural, human, "
            "technical, environmental) and by origin (accidental, deliberate). The "
            "threat catalogue serves as the basis for identifying risk scenarios."
        ),
    },
    {
        "key": "risks.vulnerability_list",
        "title": "Vulnerabilities",
        "body": (
            "Vulnerabilities are weaknesses in assets or security controls that can "
            "be exploited by threats. They are characterised by their severity, ease "
            "of exploitation and the affected assets. Vulnerability tracking helps "
            "prioritise corrective actions and reduce the attack surface."
        ),
    },
    {
        "key": "risks.iso27005_risk_list",
        "title": "ISO 27005 analyses",
        "body": (
            "ISO 27005 analyses let you conduct a risk assessment following the "
            "methodology defined by the ISO/IEC 27005 standard. Each analysis "
            "cross-references support assets, threats and vulnerabilities to identify "
            "risk scenarios, evaluate their level and propose appropriate treatment "
            "measures."
        ),
    },
]


def populate_help_content(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    for item in HELP_CONTENT_EN:
        HelpContent.objects.update_or_create(
            key=item["key"],
            language="en",
            defaults={"title": item["title"], "body": item["body"]},
        )


def reverse(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    keys = [item["key"] for item in HELP_CONTENT_EN]
    HelpContent.objects.filter(key__in=keys, language="en").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0004_alter_helpcontent_options_alter_helpcontent_body_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_help_content, reverse),
    ]

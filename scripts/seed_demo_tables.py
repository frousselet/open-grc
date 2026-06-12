"""Content catalogues for the demo seed (fictional company: Voltara Energy).

Pure data, no ORM. Imported by seed_demo_data.py.
"""

# ISO/IEC 27001:2022 Annex A : 93 controls in 4 themes.
ISO27001_SECTIONS = [
    ("A.5", "Organizational controls", [
        ("A.5.1", "Policies for information security"),
        ("A.5.2", "Information security roles and responsibilities"),
        ("A.5.3", "Segregation of duties"),
        ("A.5.4", "Management responsibilities"),
        ("A.5.5", "Contact with authorities"),
        ("A.5.6", "Contact with special interest groups"),
        ("A.5.7", "Threat intelligence"),
        ("A.5.8", "Information security in project management"),
        ("A.5.9", "Inventory of information and other associated assets"),
        ("A.5.10", "Acceptable use of information and other associated assets"),
        ("A.5.11", "Return of assets"),
        ("A.5.12", "Classification of information"),
        ("A.5.13", "Labelling of information"),
        ("A.5.14", "Information transfer"),
        ("A.5.15", "Access control"),
        ("A.5.16", "Identity management"),
        ("A.5.17", "Authentication information"),
        ("A.5.18", "Access rights"),
        ("A.5.19", "Information security in supplier relationships"),
        ("A.5.20", "Addressing information security within supplier agreements"),
        ("A.5.21", "Managing information security in the ICT supply chain"),
        ("A.5.22", "Monitoring, review and change management of supplier services"),
        ("A.5.23", "Information security for use of cloud services"),
        ("A.5.24", "Information security incident management planning and preparation"),
        ("A.5.25", "Assessment and decision on information security events"),
        ("A.5.26", "Response to information security incidents"),
        ("A.5.27", "Learning from information security incidents"),
        ("A.5.28", "Collection of evidence"),
        ("A.5.29", "Information security during disruption"),
        ("A.5.30", "ICT readiness for business continuity"),
        ("A.5.31", "Legal, statutory, regulatory and contractual requirements"),
        ("A.5.32", "Intellectual property rights"),
        ("A.5.33", "Protection of records"),
        ("A.5.34", "Privacy and protection of PII"),
        ("A.5.35", "Independent review of information security"),
        ("A.5.36", "Compliance with policies, rules and standards for information security"),
        ("A.5.37", "Documented operating procedures"),
    ]),
    ("A.6", "People controls", [
        ("A.6.1", "Screening"),
        ("A.6.2", "Terms and conditions of employment"),
        ("A.6.3", "Information security awareness, education and training"),
        ("A.6.4", "Disciplinary process"),
        ("A.6.5", "Responsibilities after termination or change of employment"),
        ("A.6.6", "Confidentiality or non-disclosure agreements"),
        ("A.6.7", "Remote working"),
        ("A.6.8", "Information security event reporting"),
    ]),
    ("A.7", "Physical controls", [
        ("A.7.1", "Physical security perimeters"),
        ("A.7.2", "Physical entry"),
        ("A.7.3", "Securing offices, rooms and facilities"),
        ("A.7.4", "Physical security monitoring"),
        ("A.7.5", "Protecting against physical and environmental threats"),
        ("A.7.6", "Working in secure areas"),
        ("A.7.7", "Clear desk and clear screen"),
        ("A.7.8", "Equipment siting and protection"),
        ("A.7.9", "Security of assets off-premises"),
        ("A.7.10", "Storage media"),
        ("A.7.11", "Supporting utilities"),
        ("A.7.12", "Cabling security"),
        ("A.7.13", "Equipment maintenance"),
        ("A.7.14", "Secure disposal or re-use of equipment"),
    ]),
    ("A.8", "Technological controls", [
        ("A.8.1", "User endpoint devices"),
        ("A.8.2", "Privileged access rights"),
        ("A.8.3", "Information access restriction"),
        ("A.8.4", "Access to source code"),
        ("A.8.5", "Secure authentication"),
        ("A.8.6", "Capacity management"),
        ("A.8.7", "Protection against malware"),
        ("A.8.8", "Management of technical vulnerabilities"),
        ("A.8.9", "Configuration management"),
        ("A.8.10", "Information deletion"),
        ("A.8.11", "Data masking"),
        ("A.8.12", "Data leakage prevention"),
        ("A.8.13", "Information backup"),
        ("A.8.14", "Redundancy of information processing facilities"),
        ("A.8.15", "Logging"),
        ("A.8.16", "Monitoring activities"),
        ("A.8.17", "Clock synchronization"),
        ("A.8.18", "Use of privileged utility programs"),
        ("A.8.19", "Installation of software on operational systems"),
        ("A.8.20", "Networks security"),
        ("A.8.21", "Security of network services"),
        ("A.8.22", "Segregation of networks"),
        ("A.8.23", "Web filtering"),
        ("A.8.24", "Use of cryptography"),
        ("A.8.25", "Secure development life cycle"),
        ("A.8.26", "Application security requirements"),
        ("A.8.27", "Secure system architecture and engineering principles"),
        ("A.8.28", "Secure coding"),
        ("A.8.29", "Security testing in development and acceptance"),
        ("A.8.30", "Outsourced development"),
        ("A.8.31", "Separation of development, test and production environments"),
        ("A.8.32", "Change management"),
        ("A.8.33", "Test information"),
        ("A.8.34", "Protection of information systems during audit testing"),
    ]),
]

NIS2_SECTIONS = [
    ("Art. 20", "Governance", [
        ("NIS2-20.1", "Management bodies approve cybersecurity risk-management measures"),
        ("NIS2-20.2", "Management bodies follow cybersecurity training"),
    ]),
    ("Art. 21", "Cybersecurity risk-management measures", [
        ("NIS2-21.a", "Policies on risk analysis and information system security"),
        ("NIS2-21.b", "Incident handling"),
        ("NIS2-21.c", "Business continuity, backup management, disaster recovery and crisis management"),
        ("NIS2-21.d", "Supply chain security, including suppliers and service providers"),
        ("NIS2-21.e", "Security in acquisition, development and maintenance, including vulnerability handling and disclosure"),
        ("NIS2-21.f", "Policies and procedures to assess the effectiveness of risk-management measures"),
        ("NIS2-21.g", "Basic cyber hygiene practices and cybersecurity training"),
        ("NIS2-21.h", "Policies and procedures on the use of cryptography and, where appropriate, encryption"),
        ("NIS2-21.i", "Human resources security, access control policies and asset management"),
        ("NIS2-21.j", "Multi-factor or continuous authentication, secured voice, video and text communications"),
    ]),
    ("Art. 23", "Reporting obligations", [
        ("NIS2-23.1", "Early warning of significant incidents within 24 hours"),
        ("NIS2-23.2", "Incident notification with initial assessment within 72 hours"),
        ("NIS2-23.3", "Final incident report within one month"),
    ]),
]

GDPR_SECTIONS = [
    ("Ch. II", "Principles", [
        ("GDPR-5", "Principles relating to processing of personal data"),
        ("GDPR-6", "Lawfulness of processing"),
    ]),
    ("Ch. III", "Rights of the data subject", [
        ("GDPR-13", "Information to be provided where personal data are collected"),
        ("GDPR-15", "Right of access by the data subject"),
        ("GDPR-16", "Right to rectification"),
        ("GDPR-17", "Right to erasure (right to be forgotten)"),
        ("GDPR-20", "Right to data portability"),
        ("GDPR-21", "Right to object"),
    ]),
    ("Ch. IV", "Controller and processor", [
        ("GDPR-25", "Data protection by design and by default"),
        ("GDPR-28", "Processor obligations and contracts"),
        ("GDPR-30", "Records of processing activities"),
        ("GDPR-32", "Security of processing"),
        ("GDPR-33", "Notification of a personal data breach to the supervisory authority"),
        ("GDPR-35", "Data protection impact assessment"),
        ("GDPR-37", "Designation of the data protection officer"),
    ]),
]

BASELINE_SECTIONS = [
    ("VSB-1", "Identity and access", [
        ("VSB-1.1", "Multi-factor authentication on all remote and privileged access"),
        ("VSB-1.2", "Quarterly access rights review for critical systems"),
        ("VSB-1.3", "Dedicated admin accounts, no daily-use privileges"),
    ]),
    ("VSB-2", "Infrastructure resilience", [
        ("VSB-2.1", "Daily backups with weekly restoration tests"),
        ("VSB-2.2", "Critical patches deployed within 14 days, others within 60 days"),
        ("VSB-2.3", "Strict network segregation between IT and OT environments"),
        ("VSB-2.4", "Centralised logging with 12-month retention"),
    ]),
    ("VSB-3", "Third parties and people", [
        ("VSB-3.1", "Security due diligence before onboarding any supplier"),
        ("VSB-3.2", "Annual security awareness training with phishing simulations"),
        ("VSB-3.3", "Incident response runbooks tested twice a year"),
    ]),
]

# Threat catalogue: (title, type, description)
THREATS = [
    ("Ransomware attack", "deliberate", "Encryption of corporate or industrial systems by a cybercrime group demanding ransom payment."),
    ("Phishing and credential theft", "deliberate", "Targeted email campaigns harvesting employee credentials to gain initial access."),
    ("Compromise of remote access", "deliberate", "Exploitation of VPN or remote maintenance gateways to reach internal networks."),
    ("Supply chain compromise", "deliberate", "Malicious code or access introduced through a software vendor or service provider."),
    ("Insider data exfiltration", "deliberate", "Disgruntled or financially motivated employee leaking sensitive data."),
    ("Denial of service on customer portal", "deliberate", "Volumetric or applicative DDoS making customer-facing services unavailable."),
    ("Sabotage of industrial control systems", "deliberate", "Intentional manipulation of SCADA/PLC setpoints to disrupt energy production."),
    ("Accidental misconfiguration", "accidental", "Erroneous change on production infrastructure exposing services or data."),
    ("Loss of key personnel", "accidental", "Departure of staff holding critical, undocumented operational knowledge."),
    ("Datacenter power failure", "environmental", "Extended electrical outage exceeding UPS and generator autonomy."),
    ("Flooding of hydro control room", "environmental", "Natural flooding event damaging control equipment at the hydro station."),
]

# Vulnerability catalogue: (title, severity, cve, description)
VULNERABILITIES = [
    ("Unpatched VPN gateway firmware", "critical", "CVE-2024-3400", "Perimeter VPN appliance running a firmware version vulnerable to unauthenticated remote code execution."),
    ("Legacy Windows hosts in OT network", "high", "", "Supervision workstations running end-of-life Windows versions that no longer receive security updates."),
    ("Weak password policy on historian database", "high", "", "Shared service accounts with non-expiring passwords on the production data historian."),
    ("Flat network between IT and OT", "critical", "", "Insufficient segmentation allows lateral movement from office IT to industrial control segments."),
    ("Missing MFA on contractor accounts", "high", "", "Third-party maintenance accounts authenticate with passwords only."),
    ("Outdated TLS configuration on customer portal", "medium", "", "Customer portal still accepts TLS 1.0/1.1 handshakes and weak cipher suites."),
    ("Log4j in vendor monitoring appliance", "high", "CVE-2021-44228", "Embedded Log4j library in the building management system reported vulnerable by the vendor."),
    ("No offline backup for SCADA configuration", "medium", "", "PLC and SCADA project files only backed up on a network share reachable from IT."),
]

# Custom indicator measurement series (about 12 monthly points each, oldest first).
INDICATOR_SERIES = {
    "phishing_click_rate": [14.2, 13.1, 12.4, 11.0, 9.8, 9.2, 8.1, 7.4, 6.9, 6.1, 5.4, 4.8],
    "mfa_coverage": [55, 58, 63, 70, 74, 79, 83, 86, 90, 93, 95, 97],
    "patch_latency_days": [42, 40, 38, 35, 33, 30, 28, 27, 24, 22, 21, 19],
    "incidents_per_month": [7, 5, 8, 6, 4, 6, 3, 5, 4, 3, 4, 2],
    "backup_success_rate": [91.5, 92.0, 93.8, 94.2, 95.0, 96.1, 95.4, 97.0, 97.8, 98.2, 98.5, 99.1],
    "soc_mttr_hours": [36, 34, 30, 28, 26, 25, 22, 20, 19, 17, 16, 14],
}

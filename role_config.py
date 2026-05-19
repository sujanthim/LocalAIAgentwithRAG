ROLE_DOCUMENT_MAP = {
    "hr":      ["HR_POLICIES.md", "employee_roster.csv", "payroll_summary_2024.csv", "TRAINING_COMPLIANCE_GUIDE.md", "benefits_enrollment.csv"],
    "billing": ["billing_records_2024.csv", "client_directory.csv"],
    "public":  ["healthcare_company_overview.md"],
}
# admin gets everything


def get_allowed_roles(filename: str) -> list[str]:
    """Return list of roles that can access this file. Admin always included."""
    roles = ["admin"]
    for role, files in ROLE_DOCUMENT_MAP.items():
        if filename in files:
            roles.append(role)
    return roles

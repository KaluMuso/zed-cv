"""Static Zambia skill lists and display maps for canonical_skills seeding."""

from app.services.canonical_skills_curated_list import CURATED_ZAMBIA_SKILLS_RAW

PARENT_BY_CANONICAL: dict[str, str] = {
    "Microsoft Excel": "Microsoft Office",
    "Microsoft Word": "Microsoft Office",
    "Microsoft PowerPoint": "Microsoft Office",
    "Microsoft Outlook": "Microsoft Office",
    "Microsoft Access": "Microsoft Office",
    "Google Sheets": "Google Workspace",
    "Google Docs": "Google Workspace",
    "Gmail": "Google Workspace",
}

ACRONYMS: frozenset[str] = frozenset(
    {
        "ifrs", "zica", "accca", "cima", "sap", "hr", "hse", "sql", "api", "aws",
        "erp", "crm", "kyc", "aml", "iso", "ohs", "ehs", "ngo", "npo", "pci",
        "dns", "vpn", "iot", "ai", "ml", "nlp", "etl", "bi", "ui", "ux", "qa",
        "qc", "pr", "seo", "sem", "cad", "bim", "hvac", "plc", "scada", "gis",
        "gps", "rfp", "rfq", "sop", "kpi", "okr", "sla", "vat", "paye", "napsa",
        "nhi", "zra", "zesco", "unza", "cbu",
    }
)

NOTES_BY_CANONICAL: dict[str, str] = {
    "IFRS": "Financial reporting standards",
    "ZICA": "Zambia Institute of Chartered Accountants",
    "ACCA": "Association of Chartered Certified Accountants",
    "CIMA": "Chartered Institute of Management Accountants",
    "Sage Evolution": "Common accounting ERP in Zambia",
    "QuickBooks": "Small-business accounting software",
    "SAP": "Enterprise resource planning suite",
    "NAPSA": "National Pension Scheme Authority (Zambia)",
    "PAYE": "Pay-as-you-earn tax withholding",
    "VAT": "Value-added tax compliance",
    "KYC": "Know your customer compliance",
    "AML": "Anti-money laundering compliance",
    "HSE": "Health, safety, and environment",
    "AutoCAD": "Computer-aided design (drafting)",
}

DISPLAY_OVERRIDES: dict[str, str] = {
    "quickbooks": "QuickBooks",
    "javascript": "JavaScript",
    "html": "HTML",
    "css": "CSS",
    "autocad": "AutoCAD",
    "power bi": "Power BI",
    "it support": "IT Support",
    "microsoft powerpoint": "Microsoft PowerPoint",
    "node.js": "Node.js",
    "ci/cd": "CI/CD",
    "amazon web services": "Amazon Web Services",
    "microsoft azure": "Microsoft Azure",
    "google sheets": "Google Sheets",
    "google docs": "Google Docs",
}

EXTRA_ALIASES: dict[str, str] = {
    "ms powerpoint": "microsoft powerpoint",
    "powerpoint": "microsoft powerpoint",
    "ppt": "microsoft powerpoint",
    "ms outlook": "microsoft outlook",
    "outlook": "microsoft outlook",
    "ms access": "microsoft access",
    "access": "microsoft access",
    "ms office": "microsoft office",
    "office": "microsoft office",
    "google sheet": "google sheets",
    "google doc": "google docs",
    "sage": "sage evolution",
    "sage 200": "sage evolution",
    "book keeping": "bookkeeping",
    "book-keeping": "bookkeeping",
    "team work": "teamwork",
    "salesmanship": "sales",
}

# Legacy alias (first 100 of curated list); prefer CURATED_ZAMBIA_SKILLS_RAW.
CURATED_RAW_TOP_100: tuple[str, ...] = CURATED_ZAMBIA_SKILLS_RAW[:100]

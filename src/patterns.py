import re

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:\+\s*91[\s.-]*)?"
    r"(?:\(?\d{2,5}\)?[\s.-]*)?"
    r"\d{6,10}"
    r"(?!\d)"
)

SSN_PATTERN = re.compile(
    r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"
)

CREDIT_CARD_PATTERN = re.compile(
    r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"
)

IPV4_PATTERN = re.compile(
    r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"
)

DATE_PATTERN = re.compile(
    r"(?:"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|"
    r"\d{1,2}(?:st|nd|rd|th)?[\s-]+"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"[\s,]+\d{4}"
    r"|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"[\s]+\d{1,2}(?:st|nd|rd|th)?[\s,]+\d{4}"
    r")"
)

DOB_CONTEXT_PATTERN = re.compile(
    r"\b(?:date\s+of\s+birth|dob|birth\s+date|born\s+on)\b"
    r"[\s:,-]*"
    r"(" + DATE_PATTERN.pattern + r")",
    re.IGNORECASE
)

PIN_CODE_PATTERN = re.compile(
    r"(?<!\d)[1-9]\d{5}(?!\d)"
)

ADDRESS_KEYWORDS = re.compile(
    r"\b(?:"
    r"registered\s+office|"
    r"corporate\s+office|"
    r"residential\s+address|"
    r"mailing\s+address|"
    r"correspondence\s+address|"
    r"residing\s+at|"
    r"located\s+at|"
    r"office\s+address|"
    r"residence\s+address|"
    r"address\s+of\s+the\s+company|"
    r"address\s+of\s+registered\s+office"
    r")\b",
    re.IGNORECASE
)

COMPANY_SUFFIX_PATTERN = re.compile(
    r"\b(?:"
    r"limited|ltd\.?|private\s+limited|pvt\.?\s*ltd\.?|"
    r"llp|inc\.?|incorporated|corporation|corp\.?|"
    r"industries|technologies|technology|solutions|"
    r"services|systems|bank|trust|foundation"
    r")\b",
    re.IGNORECASE
)

PERSON_CONTEXT_PATTERN = re.compile(
    r"\b(?:"
    r"director|promoter|chairman|"
    r"managing\s+director|joint\s+managing\s+director|"
    r"whole[-\s]?time\s+director|"
    r"independent\s+director|"
    r"chief\s+executive\s+officer|ceo|"
    r"chief\s+financial\s+officer|cfo|"
    r"company\s+secretary|"
    r"compliance\s+officer|"
    r"contact\s+person|"
    r"key\s+managerial\s+personnel|"
    r"promoter\s+selling\s+shareholder"
    r")\b",
    re.IGNORECASE
)

COMPANY_CONTEXT_PATTERN = re.compile(
    r"\b(?:"
    r"company|corporate|promoter|"
    r"registrar|auditor|banker|"
    r"lead\s+manager|"
    r"book\s+running\s+lead\s+manager|"
    r"registrar\s+to\s+the\s+offer|"
    r"statutory\s+auditor|"
    r"legal\s+counsel|"
    r"credit\s+rating\s+agency|"
    r"research\s+report|"
    r"subsidiary|"
    r"associate\s+company|"
    r"group\s+company"
    r")\b",
    re.IGNORECASE
)

GENERIC_COMPANY_FALSE_POSITIVES = {
    "offer",
    "company",
    "corporate",
    "board",
    "management",
    "investors",
    "investor",
    "shareholders",
    "shareholder",
    "directors",
    "director",
    "committee",
    "committee of the board",
    "business",
    "services",
    "systems",
    "solutions",
    "industries",
    "technology",
    "technologies",
    "bank",
    "trust",
    "foundation",
    "limited",
    "private limited",
    "corporation",
    "corporate identity number",
    "book running lead managers",
    "lead managers",
    "registrar",
    "auditor"
}

PERSON_EXCLUSION_TERMS = {
    "offer",
    "offers",
    "directors",
    "director",
    "promoters",
    "promoter",
    "shareholder",
    "shareholders",
    "selling shareholder",
    "selling shareholders",
    "key managerial personnel",
    "managerial personnel",
    "reference rate",
    "pre-offer",
    "post-offer",
    "pursuant",
    "exchanges",
    "website",
    "websites",
    "floor price",
    "cap price",
    "risks",
    "parents branch",
    "raj esh branch",
    "sangeeta branch",
    "business",
    "company",
    "companies",
    "corporate",
    "management",
    "investors",
    "investor",
    "anchor investors",
    "registered office",
    "corporate office",
    "office",
    "taluka",
    "district",
    "village",
    "road",
    "street",
    "marg",
    "lane",
    "baner",
    "pune",
    "mumbai",
    "maharashtra",
    "india",
    "chakan taluka - khed",
    "floor price",
    "plot no",
    "plot number",
    "widely circulated marathi daily newspaper",
    "waterloo industrial",
    "waterloo industrial park",
    "bandra kurla complex",
    "bandra east",
    "appasaheb marathe marg",
    "mutual funds",
    "mutual fund",
    "industrial park",
    "business centre",
    "business center",
    "facility",
    "waterloo industrial",
}


COMPANY_EXCLUSION_TERMS = {
    "anchor investors",
    "registrar of companies",
    "registrar of companies maharashtra",
    "registered office",
    "corporate office",
    "office",
    "tower 2",
    "montreal business centre",
    "indian accounting standards",
    "ind as",
    "care report",
    "the care report",
    "promoter selling shareholders",
    "key managerial personnel",
    "group companies",
    "net proceeds",
    "supa facility",
    "calling and employment act",
    "the practicing company",
    "plot no",
    "goods and services tax",
    "government",
    "ministry of corporate affairs",
    "pune metropolitan region development authority",
    "board",
    "directors",
    "management",
    "investors",
    "shareholders",
    "shareholder",
    "offer",
    "pre-offer",
    "post-offer",
    "floor price",
    "cap price",
    "reference rate",
    "risk factors",
    "website",
    "exchanges",
    "private limited",
    "limited",
    "india limited",
    "advisory private limited"
}


LEGAL_OR_REGULATORY_TERMS = {
    "sebi",
    "companies act",
    "securities and exchange board of india",
    "ministry of corporate affairs",
    "registrar of companies",
    "income tax act",
    "goods and services tax",
    "gst",
    "indian accounting standards",
    "ind as",
    "calling and employment act",
    "companies law",
    "law",
    "regulation",
    "regulations",
    "authority",
    "government",
    "ministry",
    "department"
}
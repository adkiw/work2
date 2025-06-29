# Shared constants and helpers

# List of European countries (name, ISO code)
EU_COUNTRIES = [
    ("", ""),
    ("Lietuva", "LT"), ("Baltarusija", "BY"), ("Latvija", "LV"), ("Lenkija", "PL"), ("Vokietija", "DE"),
    ("Prancūzija", "FR"), ("Ispanija", "ES"), ("Italija", "IT"), ("Olandija", "NL"), ("Belgija", "BE"),
    ("Austrija", "AT"), ("Švedija", "SE"), ("Suomija", "FI"), ("Čekija", "CZ"), ("Slovakija", "SK"),
    ("Vengrija", "HU"), ("Rumunija", "RO"), ("Bulgarija", "BG"), ("Danija", "DK"), ("Norvegija", "NO"),
    ("Šveicarija", "CH"), ("Kroatija", "HR"), ("Slovėnija", "SI"), ("Portugalija", "PT"), ("Graikija", "GR"),
    ("Airija", "IE"), ("Didžioji Britanija", "GB"),
]


def country_flag(code: str) -> str:
    """Return emoji flag for ISO country code."""
    if not code or len(code) != 2:
        return ""
    offset = 127397
    return chr(ord(code[0].upper()) + offset) + chr(ord(code[1].upper()) + offset)

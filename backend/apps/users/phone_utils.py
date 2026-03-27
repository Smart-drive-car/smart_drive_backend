import re


def normalize_phone_number(value: str) -> str:
    clean_phone = re.sub(r'\D', '', str(value or ''))
    if len(clean_phone) >= 9:
        return clean_phone[-9:]
    raise ValueError('Phone number must contain at least 9 digits.')
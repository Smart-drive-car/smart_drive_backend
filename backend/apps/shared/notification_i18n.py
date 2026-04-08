import re


SERVICE_TYPE_TRANSLATIONS = {
    "moy almashtirildi": {"uz": "Moy almashtirildi", "ru": "Замена масла"},
    "oil change": {"uz": "Moy almashtirildi", "ru": "Замена масла"},
    "oil replacement": {"uz": "Moy almashtirildi", "ru": "Замена масла"},
    "техническое обслуживание": {"uz": "Texnik xizmat", "ru": "Техническое обслуживание"},
    "то": {"uz": "Texnik xizmat", "ru": "Техническое обслуживание"},
}


def _extract_first_int(text):
    if not text:
        return None
    match = re.search(r"(\d[\d\s]*)", str(text))
    if not match:
        return None
    return match.group(1).replace(" ", "")


def _fmt_km(value):
    try:
        number = int(str(value).replace(" ", ""))
        return f"{number:,}".replace(",", " ")
    except Exception:
        return str(value)


def _extract_service_type_from_body(body):
    """Extract service type name from body like: 'Moy almashtirildi service was created by Workshop Name.'"""
    if not body:
        return None, None
    marker = " service was created by "
    if marker not in body:
        return None, None
    parts = body.split(marker)
    return parts[0].strip(), parts[1].rstrip(".").strip()


def _translate_service_type(service_type_name):
    """Translate service type to Uzbek and Russian."""
    if not service_type_name:
        return None, None
    
    key = service_type_name.lower().strip()
    if key in SERVICE_TYPE_TRANSLATIONS:
        mapping = SERVICE_TYPE_TRANSLATIONS[key]
        return mapping.get("uz"), mapping.get("ru")
    
    return service_type_name, service_type_name


def localize_notification(title, body, data=None):
    data = data or {}
    event = data.get("event")

    title_text = title or ""
    body_text = body or ""

    if event == "warning_1000km":
        current_mileage = _extract_first_int(title_text)
        remaining = _extract_first_int(body_text)

        title_res = f"{_fmt_km(current_mileage)}km" if current_mileage else title_text

        if remaining:
            body_uz = f"{_fmt_km(remaining)}km dan so'ng moy almashtirishingiz kerak"
            body_ru = f"Через {_fmt_km(remaining)} км вам нужно заменить масло"
        else:
            body_uz = body_text
            body_ru = body_text

        return {
            "title": title_res,
            "body": {"uz": body_uz, "ru": body_ru},
        }

    if event == "warning_overdue":
        current_mileage = _extract_first_int(title_text) or _extract_first_int(body_text)

        title_res = f"{_fmt_km(current_mileage)}km" if current_mileage else title_text

        if current_mileage:
            body_uz = (
                f"Mashinaning umumiy yurgan masofasi taxminan: {_fmt_km(current_mileage)} km "
                "Agar bu haqiqiy yurgan masofadan farq qilsa, iltimos, to'g'ri qiymatni kiriting!"
            )
            body_ru = (
                f"Текущий пробег автомобиля примерно: {_fmt_km(current_mileage)} км. "
                "Если есть большая разница с фактическим пробегом, пожалуйста, введите корректный пробег."
            )
        else:
            body_uz = body_text
            body_ru = body_text

        return {
            "title": title_res,
            "body": {"uz": body_uz, "ru": body_ru},
        }

    if event == "service_created":
        service_type_name, workshop_name = _extract_service_type_from_body(body_text)
        service_uz, service_ru = _translate_service_type(service_type_name)
        
        # If the title is still the old static text, fallback to workshop name.
        # Otherwise, the title will be the description (or whatever was saved during creation).
        if title_text == "New service created":
            title_res = workshop_name if workshop_name else title_text
        else:
            title_res = title_text
            
        body_uz = service_uz or body_text
        body_ru = service_ru or body_text

        return {
            "title": title_res,
            "body": {"uz": body_uz, "ru": body_ru},
        }

    return {
        "title": title_text,
        "body": {"uz": body_text, "ru": body_text},
    }

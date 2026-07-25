import re
from datetime import date


def only_digits(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\D", "", value)


def normalize_cpf(value: str) -> str:
    digits = only_digits(value) or ""
    if len(digits) != 11:
        raise ValueError("CPF deve conter 11 dígitos.")
    return digits


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = only_digits(value) or ""
    if len(digits) not in {10, 11}:
        raise ValueError("Telefone deve conter 10 ou 11 dígitos.")
    return digits


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

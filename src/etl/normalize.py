import re


def strip_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


def unify_floor_format(value: str | None) -> str | None:
    if not value:
        return value
    value = value.strip()
    match = re.match(r"^(\d+)\s*樓?$", value)
    if match:
        return f"{match.group(1)}/F"
    match = re.match(r"^(\d+)\s*/\s*F$", value, re.IGNORECASE)
    if match:
        return f"{match.group(1)}/F"
    return value


def normalize_row(row: dict, rules: list[str]) -> dict:
    result = dict(row)
    for rule in rules:
        if rule == "strip_whitespace":
            for key in result:
                if isinstance(result[key], str):
                    result[key] = strip_whitespace(result[key])
        elif rule == "unify_floor_format" and "floor" in result:
            result["floor"] = unify_floor_format(result.get("floor"))
    return result

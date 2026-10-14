"""Command-name normalization shared by extraction and scoring."""

import re

IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
TYPE_ALIASES = {
    "str": "string",
    "string": "string",
    "int": "integer",
    "integer": "integer",
    "float": "number",
    "number": "number",
    "bool": "boolean",
    "boolean": "boolean",
}
PLACEHOLDERS = {
    "string": "sample",
    "integer": "1",
    "number": "1",
    "boolean": "true",
}


def slug(value: str) -> str:
    """Fold a source identifier into a lowercase command token."""
    text = value.strip()
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = text.replace("-", "_")
    text = re.sub(r"[^A-Za-z0-9_]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").lower()
    return text


def is_ident(value: str) -> bool:
    return bool(IDENT.fullmatch(value))


def normalize_type(value: str) -> str:
    return TYPE_ALIASES.get(value.strip().lower(), "string")


def placeholder(type_name: str) -> str:
    return PLACEHOLDERS.get(type_name, "sample")

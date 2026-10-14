"""Domain errors for inventory assembly and catalog scoring."""


class CatalogError(Exception):
    """A caller-supplied inventory cannot be scored."""

    def __init__(self, message: str, field: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.field = field

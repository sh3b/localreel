class DomainError(Exception):
    pass


class UnsupportedSource(DomainError):
    """The submitted URL is not from a supported platform."""

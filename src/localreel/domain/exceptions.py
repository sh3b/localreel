class DomainError(Exception):
    pass


class UnsupportedSource(DomainError):
    """The submitted URL is not from a supported platform."""


class DuplicateVideo(DomainError):
    """A video with the same source key exists."""

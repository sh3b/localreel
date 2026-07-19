class DomainError(Exception):
    pass


class InvalidStatusTransition(DomainError):
    pass


class UnsupportedSource(DomainError):
    """The submitted URL is not from a supported platform."""


class VideoNotFound(DomainError):
    pass

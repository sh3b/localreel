from dataclasses import dataclass

from localreel.domain.messages import Command


@dataclass(frozen=True)
class SubmitURL(Command):
    url: str

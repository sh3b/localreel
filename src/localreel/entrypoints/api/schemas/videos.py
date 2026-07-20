from pydantic import BaseModel


class SubmitURLRequest(BaseModel):
    url: str

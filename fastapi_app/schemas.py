from pydantic import BaseModel

class ConfigResponse(BaseModel):
    config: str

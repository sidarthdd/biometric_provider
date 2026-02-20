from pydantic import BaseModel

class InitialiseRequest(BaseModel):
    ClientId: str
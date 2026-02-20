from pydantic import BaseModel

class IdentifyRequest(BaseModel):
    TimeLimit: int

class IdentifyResponse(BaseModel):
    Result: int
    SpoofingDetected: bool
    Score: float
    CaptureDuration: int
    CaptureImage: str
    ReferenceData: str

from pydantic import BaseModel

class BoardingRequest(BaseModel):
    Airline: str
    FlightNumber: str
    TravelDate: str
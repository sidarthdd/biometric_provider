from fastapi import FastAPI
import models
from log.logger import setup_logger

logger = setup_logger()
app = FastAPI()


@app.post("/api/initialize")
async def initialize(InitializeRequest: models.InitialiseRequest):
    logger.info(f"Initializing biometric provider for client {InitializeRequest.ClientId}")
    InitialiseResponse = {
        "LiveImageSupport": "MJPEGSTREAM",
        "VideoStreamUrl": None,
        "LiveImageMaxPullRate": 1,
        "RequestDisplayFeedback": 0,
        "PaxDetectionAutoReset": False
    }
    return InitialiseResponse

@app.post("/api/startBoarding")
async def start_boarding(boardingRequest: models.BoardingRequest):
    logger.info(f"Starting boarding process for flight {boardingRequest.FlightNumber} on {boardingRequest.TravelDate}")
    return {}

@app.post("/api/stopBoarding")
async def stop_boarding():
    logger.info("Stopping boarding process")
    return {}
from fastapi import FastAPI, Request, Response
import models
from log.logger import setup_logger
import cv2
import sys

logger = setup_logger()
app = FastAPI()
cap = cv2.VideoCapture(0)
if sys.platform.startswith('win'):
    cap.set(cv2.CAP_PROP_BACKEND, cv2.CAP_DSHOW)


@app.get("/api/status")
async def get_status():
    if not cap.isOpened():
        logger.error("Unable to access the webcam.")
        return {"OverallStatus": "KO", "Message": "Unable to access the camera."}
    ret, frame = cap.read()
    if not ret:
        logger.error("Unable to read from the webcam.")
        return {"OverallStatus": "KO", "Message": "Unable to read from the camera."}
    return {"OverallStatus": "OK", "Message": ""}

@app.get("/")
async def stream():
    ret, frame = cap.read()
    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(content=jpeg.tobytes(), media_type="image/jpeg")

@app.post("/api/initialize")
async def initialize(InitializeRequest: models.InitialiseRequest, request: Request):
    logger.info(f"Initializing biometric provider for client {InitializeRequest.ClientId}")
    video_stream_url = str(request.base_url)
    InitialiseResponse = {
        "LiveImageSupport": "JPEGPULL",
        "VideoStreamUrl": video_stream_url,
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

@app.post("/api/identify")
async def identify(identifyRequest: models.IdentifyRequest) -> models.IdentifyResponse:
    return models.IdentifyResponse(
        Result=2,
        SpoofingDetected=False,
        Score=0.996,
        CaptureDuration=2200,
        CaptureImage="ABCD…",
        ReferenceData="M1MUELLER/MAX MR      EABCDEF MUCTXLLH 412  42 C12A 1234513B>50B0          2A             0                           0"
    )
    
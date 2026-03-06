from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import models
from log.logger import setup_logger
import cv2
import sys
import threading
from contextlib import asynccontextmanager
import base64
import ffmpeg
import requests

logger = setup_logger()

camera = None
lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global camera
    try:
        if sys.platform.startswith('win'):
            camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        else:
            camera = cv2.VideoCapture(0)
        
        if not camera.isOpened():
            logger.error("Failed to initialize camera")
            raise RuntimeError("Camera initialization failed")
        
        logger.info("Camera initialized successfully")
        yield
    finally:
        if camera is not None:
            camera.release()
            logger.info("Camera released")
        cv2.destroyAllWindows()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_frame():
    global camera
    if camera is None or not camera.isOpened():
        logger.error("Camera is not available")
        return None, False
    with lock:
        ret, frame = camera.read()
    return frame, ret

@app.get("/")
async def mjpeg_stream():
    def generate_frames():
        while True:
            frame, ret = get_frame()
            if not ret or frame is None:
                logger.error("Failed to capture frame for MJPEG stream")
                time.sleep(0.1)
                continue
                
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                frame_bytes = jpeg.tobytes()
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                )
            time.sleep(0.03)
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/video")
async def h264_stream():
    def generate_video():
        writer = None
        frame_buffer = []
        fps = 30
        
        while True:
            frame, ret = get_frame()
            if not ret or frame is None:
                time.sleep(0.1)
                continue
            
            # Pre-encode frame to H.264 segment
            height, width = frame.shape[:2]
            if writer is None:
                writer = ffmpeg.write_frames(
                    width=width, height=height, pix_fmt_in='bgr24', pix_fmt_out='yuv420p',
                    logger=logger
                )
            
            # Yield H.264 NAL units (segmented for streaming)
            out = ffmpeg.encode_frame(writer, frame)
            for packet in out:
                yield packet.tobytes()
            
            time.sleep(1.0 / fps)
    
    return StreamingResponse(
        generate_video(),
        media_type="video/mp4; codecs=h264",  # Or "video/h264" for raw
        headers={"Cache-Control": "no-cache"}
    )

@app.get("/api/status")
async def get_status():
    frame, ret = get_frame()
    if frame is None:
        return {"OverallStatus": "KO", "Message": "Camera is not available."}
    if not ret:
        logger.error("Unable to read from the webcam.")
        return {"OverallStatus": "KO", "Message": "Unable to read from the camera."}
    return {"OverallStatus": "OK", "Message": ""}

@app.get("/api/liveImage")
async def stream():
    frame, ret = get_frame()
    if not ret or frame is None:
        logger.error("Failed to capture frame from camera.")
        return Response(content=b'', media_type="image/jpeg")
    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(content=jpeg.tobytes(), media_type="image/jpeg")

@app.post("/api/initialize")
async def initialize(InitializeRequest: models.InitialiseRequest, request: Request):
    logger.info(f"Initializing biometric provider for client {InitializeRequest.ClientId}")
    video_stream_url = str(request.base_url)
    InitialiseResponse = {
        "LiveImageSupport": "MJPEGSTREAM",
        "VideoStreamUrl": video_stream_url,
        "LiveImageMaxPullRate": 10,
        "RequestDisplayFeedback": 0,
        "PaxDetectionAutoReset": False
    }
    return InitialiseResponse

@app.post("/api/startBoarding")
async def start_boarding(request: Request):
    # logger.info(f"Starting boarding process for flight {boardingRequest.FlightNumber} on {boardingRequest.TravelDate}")
    body = await request.body()
    logger.info(f"Received start boarding request with body: {body.decode()}")
    return {}

@app.post("/api/display")
async def display(request: Request):
    body = await request.body()
    logger.info(f"Received display request with body: {body.decode()}")
    return {}

@app.post("/api/stopBoarding")
async def stop_boarding():
    logger.info("Stopping boarding process")
    return {}

@app.post("/api/identify")
def identify(identifyRequest: models.IdentifyRequest) -> models.IdentifyResponse:
    frame, ret = get_frame()
    if not ret or frame is None:
        logger.error("Failed to capture frame for identification")
        return models.IdentifyResponse(
            Result=0,
            SpoofingDetected=False,
            Score=0.0,
            CaptureDuration=0,
            CaptureImage="",
            ReferenceData=""
        )
    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if ret:
        capture_image_b64 = base64.b64encode(jpeg.tobytes()).decode('utf-8')
    else:
        logger.error("Failed to encode frame for identification")
        capture_image_b64 = ""

    try: 
        api_url = "http://13.216.238.204:8000/auth/recognize"
        files = {'file': ('capture.jpg', jpeg.tobytes(), 'image/jpeg')}
        header = {'accept': 'application/json'}
        response = requests.post(api_url, files=files, headers=header)
        if response.status_code == 200:
            logger.info(f"Received response from recognition API: {response.json()}")
            response_data = response.json()
            if response_data.get("recognized"):
                result = 2
            else:
                result = 1
        else:
            result = 1
    except Exception as e:
        result = 1
        logger.error(f"Error occurred while setting API URL: {e}")
    return models.IdentifyResponse(
        Result=result,
        SpoofingDetected=False,
        Score=0.996,
        CaptureDuration=2200,
        CaptureImage=capture_image_b64,
        ReferenceData="M1MUELLER/MAX MR      EABCDEF MUCTXLLH 412  42 C12A 1234513B>50B0          2A             0                           0"
    )

@app.post("/api/completed")
async def complete(request: Request):
    body = await request.body()
    logger.info(f"Received completed request with body: {body.decode()}")
    return {}

@app.post("/api/cancel")
async def cancel(request: Request):
    body = await request.body()
    logger.info(f"Received cancel request with body: {body.decode()}")
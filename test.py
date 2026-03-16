import cv2

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not camera.isOpened():
    print("Failed to initialize camera")
else:
    while True:
        ret, frame = camera.read()
        if not ret:
            print("Failed to capture frame")
            break
        cv2.imshow('Camera Test', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
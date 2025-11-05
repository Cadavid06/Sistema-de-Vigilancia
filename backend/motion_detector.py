import cv2
import datetime
from gpio_control import encender_verde, apagar_verde


class MotionDetector:
    def __init__(self, source=0, min_area=2000):
        self.capture = cv2.VideoCapture(source)
        self.first_frame = None
        self.min_area = min_area

    def get_frame(self):
        success, frame = self.capture.read()
        if not success:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.first_frame is None:
            self.first_frame = gray
            return frame

        delta = cv2.absdiff(self.first_frame, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) < self.min_area:
                continue
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            motion_detected = True

        if motion_detected:
            encender_verde()
            cv2.putText(
                frame,
                f"Movimiento detectado",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
        else:
            apagar_verde()

        return frame

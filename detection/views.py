

import base64
import numpy as np
import cv2
from threading import Lock
from rest_framework.views import APIView
from rest_framework.response import Response
from .ml.predict import predict_frame14  # fully multi-camera safe

# Global camera locks
camera_locks = {}

class DetectAPIView14(APIView):

    def post(self, request):
        image_data = request.data.get("image")
        camera_id = request.data.get("camera_id", "default")

        if not image_data:
            return Response({"error": "No image provided"}, status=400)

        # Decode base64 image
        try:
            header, imgstr = image_data.split(';base64,')
            img_bytes = base64.b64decode(imgstr)
        except (ValueError, TypeError):
            return Response({"error": "Invalid image format"}, status=400)

        # Convert to OpenCV image
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return Response({"error": "Unable to decode image"}, status=400)

        # Resize to model expected size
        expected_size = (160, 160)
        frame = cv2.resize(frame, expected_size)

        # Thread-safe prediction
        lock = camera_locks.setdefault(camera_id, Lock())
        with lock:
            # Pass **single frame** to predict_frame14
            label, confidence = predict_frame14(frame, camera_id)

        if label is None:
            return Response({"status": f"Collecting frames for camera {camera_id}..."})

        return Response({
            "camera_id": camera_id,
            "label": label,
            "confidence": round(confidence, 2)
        })
    

import base64
import numpy as np
import cv2
from rest_framework.views import APIView
from rest_framework.response import Response
from detection.ml.predict import predict_frame_multi  # fully multi-camera safe
from cameras.models import Camera
class DetectAPIViewUpdate(APIView):
    
    def post(self, request):
        image_data = request.data.get("image")
        camera_id = request.data.get("camera_id")

        if not image_data or not camera_id:
            return Response({"error": "Image and camera_id are required"}, status=400)

        # Decode base64 image
        try:
            header, imgstr = image_data.split(';base64,')
            img_bytes = base64.b64decode(imgstr)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception:
            return Response({"error": "Invalid image format"}, status=400)

        if frame is None:
            return Response({"error": "Unable to decode image"}, status=400)

        # **Do NOT resize here**, predict_frame14 handles it

        # Predict using multi-camera safe function
        label, confidence = predict_frame_multi(frame, camera_id)

        if label is None:
            return Response({"status": f"Collecting frames for camera {camera_id}..."})

        return Response({
            "camera_id": camera_id,
            "label": label,
            "confidence": round(confidence, 2)
        })
    

# new for camera selected apply the camera
# detection/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from cameras.models import Camera
import base64
import numpy as np
import cv2
from detection.ml.predict import predict_frame_multi

class DetectAPIView(APIView):
    """
    Receives base64 image + camera_name
    Returns live prediction
    """
    def post(self, request):
        image_data = request.data.get("image")
        camera_name = request.data.get("camera_name")

        if not image_data or not camera_name:
            return Response({"error": "Image and camera_name required"}, status=400)

        # Validate camera ownership
        try:
            Camera.objects.get(name=camera_name, user=request.user)
        except Camera.DoesNotExist:
            return Response({"error": "Camera not authorized"}, status=403)

        try:
            header, imgstr = image_data.split(";base64,")
            img_bytes = base64.b64decode(imgstr)
            frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return Response({"error": "Invalid image format"}, status=400)

        if frame is None:
            return Response({"error": "Cannot decode image"}, status=400)

        label, confidence = predict_frame_multi(frame, camera_name)
        if label is None:
            return Response({"status": f"Collecting frames for {camera_name}..."})

        return Response({
            "camera_name": camera_name,
            "label": label,
            "confidence": round(confidence, 2)
        })
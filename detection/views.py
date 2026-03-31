

import base64
import numpy as np
import cv2
from threading import Lock
from rest_framework.views import APIView
from rest_framework.response import Response
from .ml.predict import predict_frame14  # fully multi-camera safe
from alert.models import Alert

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
       
        #save alert if suspicious
        if label == 'Suspicious':
            try:
                Alert.objects.create(
                user= self.request.user,
                camera=camera_id,
                alert_type="suspicious",
                confidence=confidence
            )
            except Alert.DoesNotExist:
                pass

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
from detection.ml.predict import predict_frame_multi ,predict_frame_multi15 # fully multi-camera safe
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
        #save alert if suspicious
        if label == 'Suspicious':
            try:
                Alert.objects.create(
                user= self.request.user,
                camera=camera_id,
                alert_type="suspicious",
                confidence=confidence
            )
            except Alert.DoesNotExist:
                pass
        return Response({
            "camera_id": camera_id,
            "label": label,
            "confidence": round(confidence, 2)
        })
    

# new for camera selected apply the camera
from rest_framework.views import APIView
from rest_framework.response import Response
from cameras.models import Camera
from detection.ml.predict import predict_frame_multi15
import base64
import numpy as np
import cv2


class DetectAPIView(APIView):

    def post(self, request):
        image_data = request.data.get("image")
        camera_name = request.data.get("camera_name")

        if not image_data or not camera_name:
            return Response({
                "error": "image and camera_name required"
            }, status=400)

        # ---------------- camera validation ----------------
        camera = Camera.objects.filter(name=camera_name, user=request.user).first()

        if not camera:
            return Response({
                "error": "Camera not found or unauthorized"
            }, status=403)

        # ---------------- decode image ----------------
        try:
            header, imgstr = image_data.split(";base64,")
            img_bytes = base64.b64decode(imgstr)
            frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return Response({
                "error": "Invalid image format"
            }, status=400)

        if frame is None:
            return Response({
                "error": "Frame decode failed"
            }, status=400)

        # ---------------- prediction ----------------
        try:
            label, confidence = predict_frame_multi15(frame, camera_name)
        except Exception as e:
            print("[VIEW ERROR]", e)
            return Response({
                "error": "Prediction failed"
            }, status=500)

        # ---------------- collecting state ----------------
        if label is None:
            return Response({
                "status": "collecting",
                "label": None,
                "confidence": None,
                "camera_name": camera_name
            })

        # ---------------- success response ----------------
        return Response({
            "status": "ok",
            "camera_name": camera_name,
            "label": label,
            "confidence": round(confidence, 2)
        })


frame_counters = {}  # camera_name ভিত্তিক counter
class DetectAPIViewSikp(APIView):
    def post(self, request):
        image_data = request.data.get("image")
        camera_name = request.data.get("camera_name")
        camera_id = request.data.get('camera_id')

        if not image_data or not camera_name:
            return Response({"error": "Image and camera_name required"}, status=400)

        # Validate camera ownership
        try:
            Camera.objects.get(name=camera_name, user=request.user)
        except Camera.DoesNotExist:
            return Response({"error": "Camera not authorized"}, status=403)

        # 🔹 Initialize counter if not exists
        if camera_name not in frame_counters:
            frame_counters[camera_name] = 0

        # 🔹 Increment counter
        frame_counters[camera_name] += 1

        # 🔹 Skip logic (2 skip, 1 process)
        if frame_counters[camera_name] % 3 != 0:
            return Response({
                "status": f"Frame skipped for {camera_name}"
            })

        # 🔹 Decode image
        try:
            header, imgstr = image_data.split(";base64,")
            img_bytes = base64.b64decode(imgstr)
            frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return Response({"error": "Invalid image format"}, status=400)

        if frame is None:
            return Response({"error": "Cannot decode image"}, status=400)

        # 🔹 Prediction
        label, confidence = predict_frame_multi(frame, camera_name)

        if label is None:
            return Response({"status": f"Collecting frames for {camera_name}..."})

        # 🔹 Save alert
        if label == 'Suspicious':
            try:
                Alert.objects.create(
                    user=self.request.user,
                    camera_id=camera_id,
                    alert_type="suspicious",
                    confidence=confidence
                )
            except Exception:
                pass

        return Response({
            "camera_name": camera_name,
            "label": label,
            "confidence": round(confidence, 2)
        })
    

# for video upload and prediction
# detection/views.py

from rest_framework import viewsets
from rest_framework.response import Response
from django.conf import settings

from .models import VideoPrediction
from .serializers import VideoPredictionSerializer
from .ml.predict import run_video_prediction, model


class VideoPredictionViewSet(viewsets.ModelViewSet):
    queryset = VideoPrediction.objects.all()
    serializer_class = VideoPredictionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        video_obj = serializer.save()

        video_path = video_obj.video.path

        # ---------------- ML PREDICTION ----------------
        final, suspicious, normal = run_video_prediction(video_path, model)

        video_obj.final_result = final
        video_obj.suspicious_frames = suspicious
        video_obj.normal_frames = normal
        video_obj.save()

        return Response({
            "id": video_obj.id,
            "final_result": final,
            "suspicious_frames": suspicious,
            "normal_frames": normal,
        })
import base64
from threading import Lock

import cv2
import numpy as np
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from alert.models import Alert
from cameras.models import Camera
from detection.ml.predict import (
    model,
    predict_frame14,
    predict_frame_multi,
    predict_frame_multi15,
    run_video_prediction,
)
from detection.ml.predict3dcnn import predict_frame_multi3d

from .models import VideoPrediction
from .serializers import VideoPredictionSerializer


camera_locks = {}
frame_counters = {}


def _decode_base64_frame(image_data):
    try:
        _, imgstr = image_data.split(";base64,")
        img_bytes = base64.b64decode(imgstr)
    except (ValueError, TypeError):
        raise ValidationError({"error": "Invalid image format"})

    frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValidationError({"error": "Unable to decode image"})
    return frame


def _get_camera_for_user(user, *, camera_id=None, camera_name=None):
    queryset = Camera.objects.filter(user=user)

    if camera_id is not None:
        return queryset.filter(pk=camera_id).first()

    if camera_name is not None:
        return queryset.filter(name=camera_name).first()

    return None


def _get_prediction_key(camera):
    return str(camera.pk)


def _build_alert(user, camera, confidence):
    Alert.objects.create(
        user=user,
        camera=camera,
        alert_type="suspicious",
        confidence=confidence,
    )


class DetectAPIView14(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        image_data = request.data.get("image")
        camera_id = request.data.get("camera_id")

        if not image_data or not camera_id:
            return Response({"error": "Image and camera_id are required"}, status=400)

        camera = _get_camera_for_user(request.user, camera_id=camera_id)
        if camera is None:
            return Response({"error": "Camera not found or unauthorized"}, status=403)

        try:
            frame = _decode_base64_frame(image_data)
        except ValidationError as exc:
            return Response(exc.detail, status=400)

        frame = cv2.resize(frame, (160, 160))
        prediction_key = _get_prediction_key(camera)

        lock = camera_locks.setdefault(prediction_key, Lock())
        with lock:
            label, confidence = predict_frame14(frame, prediction_key)

        if label is None:
            return Response({"status": f"Collecting frames for camera {camera.id}..."})

        if label == "Suspicious":
            _build_alert(request.user, camera, confidence)

        return Response(
            {
                "camera_id": camera.id,
                "label": label,
                "confidence": round(confidence, 2),
            }
        )


class DetectAPIViewUpdate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        image_data = request.data.get("image")
        camera_id = request.data.get("camera_id")

        if not image_data or not camera_id:
            return Response({"error": "Image and camera_id are required"}, status=400)

        camera = _get_camera_for_user(request.user, camera_id=camera_id)
        if camera is None:
            return Response({"error": "Camera not found or unauthorized"}, status=403)

        try:
            frame = _decode_base64_frame(image_data)
        except ValidationError as exc:
            return Response(exc.detail, status=400)

        prediction_key = _get_prediction_key(camera)
        label, confidence = predict_frame_multi(frame, prediction_key)

        if label is None:
            return Response({"status": f"Collecting frames for camera {camera.id}..."})

        if label == "Suspicious":
            _build_alert(request.user, camera, confidence)

        return Response(
            {
                "camera_id": camera.id,
                "label": label,
                "confidence": round(confidence, 2),
            }
        )


class DetectAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        image_data = request.data.get("image")
        camera_name = request.data.get("camera_name")

        if not image_data or not camera_name:
            return Response({"error": "image and camera_name required"}, status=400)

        camera = _get_camera_for_user(request.user, camera_name=camera_name)
        if camera is None:
            return Response({"error": "Camera not found or unauthorized"}, status=403)

        try:
            frame = _decode_base64_frame(image_data)
        except ValidationError as exc:
            return Response(exc.detail, status=400)

        prediction_key = _get_prediction_key(camera)
        try:
            label, confidence = predict_frame_multi15(frame, prediction_key)
        except Exception:
            return Response({"error": "Prediction failed"}, status=500)

        if label is None:
            return Response(
                {
                    "status": "collecting",
                    "label": None,
                    "confidence": None,
                    "camera_name": camera.name,
                }
            )

        if label == "Suspicious":
            _build_alert(request.user, camera, confidence)

        return Response(
            {
                "status": "ok",
                "camera_name": camera.name,
                "label": label,
                "confidence": round(confidence, 2),
            }
        )


class DetectAPIViewSikp(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        image_data = request.data.get("image")
        camera_name = request.data.get("camera_name")

        if not image_data or not camera_name:
            return Response({"error": "Image and camera_name required"}, status=400)

        camera = _get_camera_for_user(request.user, camera_name=camera_name)
        if camera is None:
            return Response({"error": "Camera not authorized"}, status=403)

        prediction_key = _get_prediction_key(camera)
        frame_counters[prediction_key] = frame_counters.get(prediction_key, 0) + 1

        if frame_counters[prediction_key] % 3 != 0:
            return Response({"status": f"Frame skipped for {camera.name}"})

        try:
            frame = _decode_base64_frame(image_data)
        except ValidationError as exc:
            return Response(exc.detail, status=400)

        label, confidence = predict_frame_multi(frame, prediction_key)

        if label is None:
            return Response({"status": f"Collecting frames for {camera.name}..."})

        if label == "Suspicious":
            _build_alert(request.user, camera, confidence)

        return Response(
            {
                "camera_name": camera.name,
                "label": label,
                "confidence": round(confidence, 2),
            }
        )


class Detect3DCNNAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        image_data = request.data.get("image")
        camera_name = request.data.get("camera_name")

        if not image_data or not camera_name:
            return Response({"error": "Image and camera_name required"}, status=400)

        camera = _get_camera_for_user(request.user, camera_name=camera_name)
        if camera is None:
            return Response({"error": "Camera not authorized"}, status=403)

        prediction_key = _get_prediction_key(camera)
        frame_counters[prediction_key] = frame_counters.get(prediction_key, 0) + 1

        if frame_counters[prediction_key] % 3 != 0:
            return Response({"status": f"Frame skipped for {camera.name}"})

        try:
            frame = _decode_base64_frame(image_data)
        except ValidationError as exc:
            return Response(exc.detail, status=400)

        label, confidence = predict_frame_multi3d(frame, prediction_key)

        if label is None:
            return Response({"status": f"Collecting frames for {camera.name}..."})

        if label == "Suspicious":
            _build_alert(request.user, camera, confidence)

        return Response(
            {
                "camera_name": camera.name,
                "label": label,
                "confidence": round(confidence, 2),
            }
        )


class VideoPredictionViewSet(viewsets.ModelViewSet):
    serializer_class = VideoPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoPrediction.objects.filter(user=self.request.user).select_related("camera")

    def perform_create(self, serializer):
        camera = serializer.validated_data.get("camera")
        if camera is not None and camera.user_id != self.request.user.id:
            raise PermissionDenied("You can only create predictions for your own cameras.")
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        video_obj = serializer.instance
        final, suspicious, normal = run_video_prediction(video_obj.video.path, model)

        video_obj.final_result = final
        video_obj.suspicious_frames = suspicious
        video_obj.normal_frames = normal
        video_obj.save(update_fields=["final_result", "suspicious_frames", "normal_frames"])

        return Response(
            {
                "id": video_obj.id,
                "final_result": final,
                "suspicious_frames": suspicious,
                "normal_frames": normal,
            }
        )

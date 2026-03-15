# api/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path
from cameras.views import CameraViewSet, CameraListViewSet
from detection.views import DetectAPIView, DetectAPIViewUpdate, DetectAPIView14

router = DefaultRouter()
# Camera CRUD API
router.register('cameras', CameraViewSet, basename='cameras')
# Optional: Only list cameras for dropdown
router.register('camera-list', CameraListViewSet, basename='camera-list')

urlpatterns = [
    # Legacy multi-frame API (optional)
    path("detect/", DetectAPIView14.as_view(), name="detect14"),

    # Single-frame per camera with user validation
    path("detect-update/", DetectAPIViewUpdate.as_view(), name="detect-update"),

    # Production-ready detection API (multi-camera safe)
    path("detection/", DetectAPIView.as_view(), name="detection"),
]

# Include router URLs (Camera CRUD + Camera list)
urlpatterns += router.urls

from rest_framework.routers import DefaultRouter
from cameras.views import CameraViewSet
from detection.views import DetectAPIView14,DetectAPIViewUpdate
from django.urls import path

router = DefaultRouter()
router.register('cameras',CameraViewSet,basename='cameras')




urlpatterns=[
    path("detect/", DetectAPIView14.as_view()),
    path("detect-update/", DetectAPIViewUpdate.as_view()),
]
urlpatterns += router.urls



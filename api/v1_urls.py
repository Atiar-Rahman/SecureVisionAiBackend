from rest_framework.routers import DefaultRouter
from cameras.views import CameraViewSet

router = DefaultRouter()
router.register('cameras',CameraViewSet,basename='cameras')

urlpatterns = router.urls



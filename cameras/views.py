from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from cameras.models import Camera
from cameras.serializers import CameraSerializer

class CameraViewSet(ModelViewSet):
    """
    Production-ready Camera API for AI Surveillance System.

    Features:
    - User auto-set from request.user
    - Only user's own cameras are visible/editable
    - snapshot, status, last_seen fields are readonly (AI controlled)
    - MultiPartParser/FormParser for snapshot uploads by AI
    """

    serializer_class = CameraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return only cameras owned by the logged-in user
        return Camera.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Auto-set user on creation
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Do NOT allow frontend to change the user
        serializer.save()

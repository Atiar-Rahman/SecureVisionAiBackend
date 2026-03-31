from django.db import models
from cameras.models import Camera
# Create your models here.
class VideoPrediction(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=True, blank=True)
    video = models.FileField(upload_to="videos/")
    
    final_result = models.CharField(max_length=20, null=True, blank=True)
    suspicious_frames = models.IntegerField(default=0)
    normal_frames = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.final_result}"
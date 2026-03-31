# detection/serializers.py

from rest_framework import serializers
from .models import VideoPrediction

class VideoPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoPrediction
        fields = "__all__"
        read_only_fields = (
            "final_result",
            "suspicious_frames",
            "normal_frames",
        )
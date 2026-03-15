
# only label and confidence

import os
import numpy as np
import cv2
from threading import Lock
from tensorflow.keras.models import load_model  # type: ignore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(BASE_DIR, "ml", "best_cnn_lstm_model.h5")

# Load model ONCE
model = load_model(model_path)

SEQ_LEN = 16
IMG_SIZE = 160

# Global camera buffers and locks
camera_buffers = {}
camera_locks = {}


def predict_frame14(frame, camera_id="default"):
    if frame is None or frame.size == 0:
        return None, None

    # Get camera lock
    lock = camera_locks.setdefault(camera_id, Lock())
    with lock:
        if camera_id not in camera_buffers:
            camera_buffers[camera_id] = []

        buffer = camera_buffers[camera_id]

        # Preprocess frame
        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
            frame = frame.astype("float32") / 255.0
        except Exception as e:
            print(f"Frame preprocessing error: {e}")
            return None, None

        buffer.append(frame)

        # Keep only last SEQ_LEN frames
        if len(buffer) < SEQ_LEN:
            return None, None

        buffer = buffer[-SEQ_LEN:]
        camera_buffers[camera_id] = buffer

        # Ensure consistent frame shapes
        consistent_buffer = []
        for f in buffer:
            if f.shape == (IMG_SIZE, IMG_SIZE, 3):
                consistent_buffer.append(f)
            else:
                f_resized = cv2.resize(f, (IMG_SIZE, IMG_SIZE))
                consistent_buffer.append(f_resized)

        # Convert to NumPy array
        buffer_array = np.stack(consistent_buffer, axis=0)  # (SEQ_LEN, IMG_SIZE, IMG_SIZE, 3)
        input_array = np.expand_dims(buffer_array, axis=0)  # (1, SEQ_LEN, IMG_SIZE, IMG_SIZE, 3)

        # Predict
        try:
            prediction = model.predict(input_array, verbose=0)[0][0]
        except Exception as e:
            print(f"Model prediction error: {e}")
            return None, None

        label = "Suspicious" if prediction > 0.5 else "Normal"
        confidence = float(prediction) if prediction > 0.5 else float(1 - prediction)

        return label, confidence
    


# snapshot screenshot

import numpy as np
import cv2
from django.core.files.base import ContentFile
from django.utils import timezone
from cameras.models import Camera

SEQ_LEN = 16
IMG_SIZE = 160

def predict_frame_multi(frame, camera_id):
    if frame is None or frame.size == 0:
        return None, None

    # Thread-safe buffer
    lock = camera_locks.setdefault(camera_id, Lock())
    with lock:
        buffer = camera_buffers.setdefault(camera_id, [])

        # Preprocess
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (IMG_SIZE, IMG_SIZE))
            frame_norm = frame_resized.astype("float32") / 255.0
        except Exception as e:
            print(f"Preprocessing error: {e}")
            return None, None

        buffer.append(frame_norm)
        buffer = buffer[-SEQ_LEN:]  # Keep last SEQ_LEN frames
        camera_buffers[camera_id] = buffer

        if len(buffer) < SEQ_LEN:
            return None, None  # Wait until buffer full

        # Prepare input for model
        input_array = np.expand_dims(np.stack(buffer, axis=0), axis=0)  # (1, SEQ_LEN, IMG_SIZE, IMG_SIZE, 3)

        # Predict
        try:
            prediction = model.predict(input_array, verbose=0)[0][0]
        except Exception as e:
            print(f"Model prediction error: {e}")
            return None, None

        label = "Suspicious" if prediction > 0.5 else "Normal"
        confidence = float(prediction) if prediction > 0.5 else float(1 - prediction)

        # Update snapshot ONLY if suspicious
        if label == "Suspicious":
            try:
                camera = Camera.objects.get(id=camera_id)
                _, buffer_jpg = cv2.imencode('.jpg', frame)
                filename = f"suspicious_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                camera.snapshot.save(filename, ContentFile(buffer_jpg.tobytes()), save=False)
                camera.last_seen = timezone.now()
                camera.status = "online"
                camera.save(update_fields=["snapshot", "last_seen", "status"])
            except Camera.DoesNotExist:
                print(f"Camera {camera_id} not found")
            except Exception as e:
                print(f"Snapshot save error: {e}")

        return label, confidence
    


# detection/ml/predict.py
import cv2
import numpy as np
from threading import Lock
from django.conf import settings
from cameras.models import Camera
import os

SEQ_LEN = 16
IMG_SIZE = 160

model = load_model(model_path)

camera_buffers = {}
camera_locks = {}

def predict_frame_multi15(frame, camera_name):
    if frame is None or frame.size == 0:
        return None, None

    lock = camera_locks.setdefault(camera_name, Lock())
    with lock:
        buffer = camera_buffers.setdefault(camera_name, [])

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb = cv2.resize(frame_rgb, (IMG_SIZE, IMG_SIZE))
        frame_rgb = frame_rgb.astype("float32") / 255.0

        buffer.append(frame_rgb)
        if len(buffer) < SEQ_LEN:
            return None, None

        buffer = buffer[-SEQ_LEN:]
        camera_buffers[camera_name] = buffer

        input_array = np.expand_dims(np.stack(buffer, axis=0), axis=0)
        pred = model.predict(input_array, verbose=0)[0][0]

        label = "Suspicious" if pred > 0.5 else "Normal"
        confidence = float(pred) if pred > 0.5 else float(1 - pred)

        # Save snapshot if suspicious
        if label == "Suspicious":
            try:
                cam = Camera.objects.get(name=camera_name)
                filename = f"{camera_name}_{int(cv2.getTickCount())}.jpg"
                path = os.path.join(settings.MEDIA_ROOT, "snapshots", filename)
                cv2.imwrite(path, cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
                cam.snapshot = f"snapshots/{filename}"
                cam.save(update_fields=["snapshot"])
            except Camera.DoesNotExist:
                pass

        return label, confidence
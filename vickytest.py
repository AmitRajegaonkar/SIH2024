import cv2
import face_recognition
import numpy as np
import time
from multiprocessing import Queue, Value, Process
from typing import Dict

def detect_face_and_eyes(frame):
    """
    Detect faces and determine if eyes are occluded (e.g., by sunglasses).
    Returns face locations, encodings, and a sunglasses flag for each face.
    """
    face_locations = face_recognition.face_locations(frame, model='cnn')
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    # Load Haar Cascade for eye detection
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    sunglasses_flags = []

    for (top, right, bottom, left) in face_locations:
        face_region = frame[top:bottom, left:right]
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)

        # Detect eyes in the face region
        eyes = eye_cascade.detectMultiScale(gray_face, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20))

        # If fewer than 2 eyes are detected, assume sunglasses
        sunglasses_flags.append(len(eyes) < 2)

    return face_locations, face_encodings, sunglasses_flags

def process_frame(input_buffer: Queue, output_buffer: Queue, exited: Value, criminals_db: Dict):
    """
    Process frames to detect suspects based on their face encoding and sunglasses status.
    """
    while not exited.value:
        try:
            frame, camera = input_buffer.get()
            face_locations, face_encodings, sunglasses_flags = detect_face_and_eyes(frame)

            for (location, encoding, wearing_sunglasses) in zip(face_locations, face_encodings, sunglasses_flags):
                # Match face encodings with suspects
                suspect_id = None
                matches = face_recognition.compare_faces(list(criminals_db.values()), encoding, tolerance=0.6)
                face_distances = face_recognition.face_distance(list(criminals_db.values()), encoding)
                if matches:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        suspect_id = list(criminals_db.keys())[best_match_index]

                output_buffer.put((camera, location, suspect_id, wearing_sunglasses))
        except Exception as e:
            print(f"Error in processing: {e}")

def display_results(output_buffer: Queue, exited: Value):
    """
    Display frames and results in a window.
    """
    while not exited.value:
        try:
            camera, location, suspect_id, wearing_sunglasses = output_buffer.get()
            status = "Suspect" if suspect_id else "Unknown"
            sunglasses_status = "Wearing Sunglasses" if wearing_sunglasses else "No Sunglasses"
            print(f"Camera {camera}: {status} ({sunglasses_status})")
        except Exception as e:
            print(f"Error in displaying: {e}")

def main():
    # Shared data
    input_buffer = Queue(10)
    output_buffer = Queue(10)
    exited = Value('i', 0)

    # Example suspects database (Aadhaar to encodings)
    criminals_db = {
        "123456789": np.random.rand(128),  # Replace with actual encodings
        "987654321": np.random.rand(128),
    }

    # Start processes
    camera_process = Process(target=capture_frames, args=(0, input_buffer, exited))
    processing_process = Process(target=process_frame, args=(input_buffer, output_buffer, exited, criminals_db))
    display_process = Process(target=display_results, args=(output_buffer, exited))

    camera_process.start()
    processing_process.start()
    display_process.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        with exited.get_lock():
            exited.value = 1

    camera_process.join()
    processing_process.join()
    display_process.join()

def capture_frames(camera_index, input_buffer: Queue, exited: Value):
    """
    Capture video frames from the camera.
    """
    cap = cv2.VideoCapture(camera_index)
    while not exited.value:
        ret, frame = cap.read()
        if ret:
            input_buffer.put((frame, camera_index))
        time.sleep(0.1)
    cap.release()

if __name__ == "__main__":
    main()

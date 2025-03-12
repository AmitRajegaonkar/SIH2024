import time
import cv2
import face_recognition
import requests
import numpy as np

# Open a connection to the webcam
video_capture = cv2.VideoCapture(0)


ctr = 0
names = []
embeddings = []
    
# Get all criminal db encodings
base_url = "http://172.27.229.241:8055"  # Replace with your Directus base URL
collection = "aadhaar_db"  # Replace with your collection name
api_token = "7k8V9rO8RtGRTYAeaN-NB2jVQ-DP9fzL"  # Replace with your Directus API token

# Folder to save images
headers = {
    "Authorization": f"Bearer {api_token}"
}


response = requests.get(f"{base_url}/items/{collection}", headers=headers)
if response.status_code == 200:
    items = response.json()["data"]

    for item in items:
        name:int = item.get("name")  # Replace with your actual Aadhar field
        existing_embedding = item.get("face_embedding")['data']  # Check for existing embedding
        embeddings.append(existing_embedding)
        names.append(name)

while True:
    # Capture a single frame from the webcam
    ret, frame = video_capture.read()
    
    # Convert the image to RGB (face_recognition expects RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
    
    
    
    # Find all face locations in the current frame
    face_locations = face_recognition.face_locations(small_frame)
    face_encodings = face_recognition.face_encodings(small_frame, face_locations,model="large")
    
    if ctr == 100:
    
    
        # Get all criminal db encodings
        base_url = "http://172.27.229.241:8055"  # Replace with your Directus base URL
        collection = "aadhaar_db"  # Replace with your collection name
        api_token = "7k8V9rO8RtGRTYAeaN-NB2jVQ-DP9fzL"  # Replace with your Directus API token

        # Folder to save images
        headers = {
            "Authorization": f"Bearer {api_token}"
        }
        
        
        names = []
        embeddings = []

        response = requests.get(f"{base_url}/items/{collection}", headers=headers)
        if response.status_code == 200:
            items = response.json()["data"]

            for item in items:
                name:int = item.get("name")  # Replace with your actual Aadhar field
                existing_embedding = item.get("face_embedding")['data']  # Check for existing embedding
                embeddings.append(existing_embedding)
                names.append(name)

        ctr = 0
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(embeddings, face_encoding)

        name = "Unknown"

        # If a match was found in known_face_encodings, just use the first one.
        # if True in matches:
        #     first_match_index = matches.index(True)
        #     name = known_face_names[first_match_index]

        # Or instead, use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(embeddings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = names[best_match_index]

        print(name,"Found on Aadhaar")
        # Draw a box around the face
        cv2.rectangle(rgb_frame, (left*4, top*4), (right*4, bottom*4), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(rgb_frame, (left*4, bottom*4 - 35), (right*4, bottom*4), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(rgb_frame, name, (left*4 + 6, bottom*4 - 6), font, 1.0, (255, 255, 255), 1)
    ctr += 1

    
    # Display the frame with rgb_frame
    cv2.imshow('Webcam Feed', rgb_frame)
    
    # Break the loop on pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
    time.sleep(0.1)

# Release the webcam and close all OpenCV windows
video_capture.release()
cv2.destroyAllWindows()

import math
from multiprocessing.managers import DictProxy, ValueProxy
import cv2
import multiprocessing
import face_recognition
import time
import numpy as np
import random
import requests

class TTLCache:

    def __init__(self, capacity,expiry_time):
        self.cache = dict()
        self.capacity = capacity
        self.expiry_time = expiry_time

    def get(self, key):

        # cam_key : str
        # to_delete = []

        # for cam_key in self.cache:
        #     cam,capture_time = cam_key.split(' ')
        #     if time.time() - float(capture_time) > self.expiry_time:
        #         to_delete.append(cam_key)

        # for i in to_delete:
        #     self.cache.pop(i,[])

        if key not in self.cache:
            return False
        else:
            return self.cache[key]

    def put(self, key, value):

        cam_key : str
        to_delete = []
        timings = math.inf

        for cam_key in self.cache:
            cam,capture_time = cam_key.split(' ')
            if time.time() - float(capture_time) > self.expiry_time:
                to_delete.append(cam_key)

        for i in to_delete:
            self.cache.pop(i,[])
        if len(self.cache) > self.capacity:
            for cam_key in self.cache:
                cam,capture_time = cam_key.split()
                timings = min(timings,float(capture_time))
            self.cache.pop(timings,[])

        self.cache[key] = value

    def get_keys(self):
        return self.cache.keys()

    def get_values(self):
        return self.cache.values()
    
    def clear_cache(self):
        cam_key : str
        to_delete = []
        timings = math.inf

        for cam_key in self.cache:
            cam,capture_time = cam_key.split(' ')
            if time.time() - float(capture_time) > self.expiry_time:
                to_delete.append(cam_key)

        for i in to_delete:
            self.cache.pop(i,[])
       



def image_capture(input_buffer:multiprocessing.Queue,camera:int,exited:ValueProxy,display_buffer:multiprocessing.Queue) -> None:
    video_capture = cv2.VideoCapture(camera)
    print("Width: %d, Height: %d, FPS: %d" % (video_capture.get(3), video_capture.get(4), video_capture.get(5)))

    while not exited.get():
        _, frame = video_capture.read()
        input_buffer.put((frame[:, :, ::-1],camera))
        display_buffer.put((frame[:, :, ::-1],camera))
        time.sleep(0.4)

    input_buffer.close()

def find_face(input_buffer: multiprocessing.Queue, output_buffer: multiprocessing.Queue, exited: ValueProxy) -> None:
    seen_faces = TTLCache(50, 5)  # Cache to store detected faces temporarily

    while not exited.get():
        try:
            # Get frame and camera info from the input buffer
            rgb_frame, camera = input_buffer.get()

            # Convert frame to grayscale for better contrast
            gray_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame, model='cnn')
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, model="large")

            # Process detected faces
            for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
                # Add all face encodings to the cache
                seen_faces.put(f'{camera} {time.time()}', encoding)
                # Send face details to the output buffer
                output_buffer.put((rgb_frame, (top, right, bottom, left), encoding, camera))

        except Exception as e:
            print(f"Error in find_face: {e}")
            pass

    output_buffer.close()


def id_face(input_buffer: multiprocessing.Queue, exited: ValueProxy, criminals_db: DictProxy) -> None:
    face_buffer = {}  # Store encodings for each camera to perform multi-frame averaging

    while not exited.get():
        try:
            # Get the current criminal encodings and Aadhaar numbers
            current_criminals_aadhaar = list(criminals_db.keys())
            current_criminals_encodings = list(criminals_db.values())

            # Process each face encoding from the input buffer
            frame, face_location, face_encoding, camera = input_buffer.get()

            # Maintain a buffer of encodings for each camera
            if camera not in face_buffer:
                face_buffer[camera] = []

            face_buffer[camera].append(face_encoding)

            # Limit buffer size to the last 5 frames
            if len(face_buffer[camera]) > 5:
                face_buffer[camera].pop(0)

            # Compute the average encoding for robustness
            avg_encoding = np.mean(face_buffer[camera], axis=0)

            # Compare against the criminal database
            matches = face_recognition.compare_faces(current_criminals_encodings, avg_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(current_criminals_encodings, avg_encoding)
            best_match_index = np.argmin(face_distances) if face_distances.size > 0 else -1

            if matches and best_match_index != -1 and matches[best_match_index]:
                name = current_criminals_aadhaar[best_match_index]
                print(f"Matched suspect: {name} with confidence: {1 - face_distances[best_match_index]}")
            else:
                print("No match found.")

        except Exception as e:
            print(f"Error in id_face: {e}")

def get_criminal_encodings(exited:ValueProxy,criminals_db:DictProxy):

    headers = {"Authorization": "Bearer DZOOPT4hrmVGk6UWE6i3vudeFEI4KzKQ"}

    while not exited.get():


        try:
            s = requests.Session()
            criminals_aadhaar_full:list = s.get("http://172.22.64.77:8055/items/criminal_db",headers=headers).json()['data']

            criminals = []
            for elem in criminals_aadhaar_full:
                criminals.append(elem['suspect_aadhaar_no'])

            encodings = []
            for criminal in criminals:
                encodings_full:list = s.get(f'http://172.22.64.77:8055/items/aadhaar_db/{criminal}',headers=headers).json()['data']['face_embeddings']['data']
                encodings.append(encodings_full)

            to_share = {}

            for i in range(len(criminals)):
                to_share[criminals[i]] = encodings[i]
            criminals_db.clear()
            criminals_db.update(to_share)
            print(criminals)
        except Exception as e:
            print(e)

        time.sleep(2)



if __name__ == '__main__':
    camera_feed_buffer = multiprocessing.Queue(20)
    face_finder_buffer = multiprocessing.Queue()
    op_buffer1 = multiprocessing.Queue()

    with multiprocessing.Manager() as manager:
        exited = manager.Value('i', 0)
        criminals_db = manager.dict()

        # Example criminal encodings
        criminals_db['new_criminal_aadhaar'] = [-0.11828114, 0.07956357, 0.04837852, -0.04479754, 0.01555238, -0.04518437,
                                                 -0.04853521, -0.10062246, 0.1675079, -0.11458287, 0.26003408, 0.03864092,
                                                 -0.22418344, -0.17187588, 0.02802898, 0.0627895, -0.10440664, -0.20294529,
                                                 -0.05528778, -0.02939461, -0.00044402, -0.03240493, 0.02235717, 0.06371656,
                                                 -0.13451317, -0.41535324, -0.09809691, -0.08500803, -0.04370362, -0.09034694,
                                                 -0.02382931, 0.04848665, -0.2297208, -0.04135892, -0.08105785, 0.11993658,
                                                 -0.02014706, 0.01606257, 0.15146819, 0.03427114, -0.19518404, -0.02370021,
                                                 0.02449792, 0.2667487, 0.1759817, 0.0208921, 0.03032931, 0.00515766,
                                                 0.02414094, -0.26601434, 0.05626382, 0.12741561, 0.15098101, 0.04659733,
                                                 0.05917027, -0.15662885, -0.02542595, 0.06487991, -0.15309554, 0.03481354,
                                                 -0.0230502, -0.08082525, -0.0438332, -0.01291467, 0.28980976, 0.14953798,
                                                 -0.12263983, -0.05948142, 0.16402645, -0.15991375, -0.04220742, 0.07792304,
                                                 -0.0624679, -0.19570553, -0.28872404, 0.12153728, 0.38314459, 0.12471439,
                                                 -0.1810251, 0.04498304, -0.14085367, -0.02863591, -0.00395267, 0.00265481,
                                                 -0.1431734, 0.09408367, -0.14769819, 0.02861816, 0.2074998, 0.08444692,
                                                 -0.03264844, 0.18116099, -0.00915661, 0.0930286, 0.11060259, 0.04019455,
                                                 -0.04306697, -0.02827087, -0.18844436, 0.01444913, 0.00828649, -0.12618719,
                                                 -0.04831159, 0.05336126, -0.16589423, 0.13326064, 0.05133313, -0.07115202,
                                                 -0.00049756, 0.09923077, -0.1066413, -0.09030351, 0.10827958, -0.29309285,
                                                 0.18105696, 0.16976814, 0.08657935, 0.20897472, 0.09855027, 0.0633515,
                                                 -0.05931821, -0.06674783, -0.11872901, -0.06899448, 0.06290771, -0.02426755,
                                                 0.09137052, 0.05523358]

        # Start processes
        camera_reader = multiprocessing.Process(target=image_capture, args=(camera_feed_buffer, 0, exited, op_buffer1))
        camera_reader.start()

        face_finder1 = multiprocessing.Process(target=find_face, args=(camera_feed_buffer, face_finder_buffer, exited))
        face_finder1.start()

        id_face_pro = multiprocessing.Process(target=id_face, args=(face_finder_buffer, exited, criminals_db))
        id_face_pro.start()

        while True:
            try:
                frame1, locations = op_buffer1.get()
                cv2.imshow('Cam 1', cv2.resize(frame1[:, :, ::-1], (480, 270)))
            except Exception as e:
                print(e)
                pass

            if cv2.waitKey(1) & 0xFF == ord('q'):
                with exited.get_lock():
                    exited.value = 1
                camera_feed_buffer.close()
                face_finder_buffer.close()
                break

            time.sleep(0.01)

        camera_reader.kill()
        face_finder1.kill()
        id_face_pro.kill()

        camera_reader.join()
        face_finder1.join()
        id_face_pro.join()

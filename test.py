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


def find_face(input_buffer:multiprocessing.Queue,output_buffer:multiprocessing.Queue,exited:ValueProxy) -> None: # type: ignore

    seen_faces = TTLCache(50,5)


    while not exited.get():
        rgb_frame,camera = input_buffer.get()
        known_encodings = list(seen_faces.get_values())

        face_locations = face_recognition.face_locations(rgb_frame,1,model='cnn')
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations,model="large")

        try:

            seen_faces.clear_cache()
            for (top,right,bottom,left),encoding in zip(face_locations,face_encodings):

                score = face_recognition.face_distance(known_encodings,encoding)
                score = np.append(score,[100])

                # If we have not seen similar face in past 10 seconds , add it to buffer
                if np.min(score) > 0.6:
                    seen_faces.put(f'{camera} {time.time()}',encoding)
                    output_buffer.put((rgb_frame,(top,right,bottom,left),encoding,camera))
        except:
            pass




        # time.sleep(0.01)
    output_buffer.close()


def id_face(input_buffer:multiprocessing.Queue,exited:ValueProxy,criminals_db:DictProxy): # type: ignore
    headers = {"Authorization": "Bearer DZOOPT4hrmVGk6UWE6i3vudeFEI4KzKQ"}

    while not exited.get():
        current_criminals_aadhaar = criminals_db.keys()
        current_criminals_encodings = criminals_db.values()



        frame,face_location,face_encoding,camera = input_buffer.get()
        print("Got a face",len(current_criminals_encodings))

        if len(current_criminals_encodings):
        # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(current_criminals_encodings, face_encoding,tolerance=0.5)
            name = "Unknown"

            # TODO : Upload to direct us - frame , face_location , time , camera - location
            face_distances = face_recognition.face_distance(current_criminals_encodings, face_encoding)

            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = current_criminals_aadhaar[best_match_index]
                try:
                    s =requests.Session()
                    top,right,bottom,left = face_location
                    crop = frame[top:bottom,left:right,::-1]
                    cv2.imwrite("frame.jpg",crop)
                    with open("frame.jpg",'rb') as f:
                        response = s.post("http://172.22.64.77:8055/files",headers=headers,files={"file":("image.jpg", f, "image/jpeg")}).json()['data']
                        print(response['id'])
                        to_add = s.post("http://172.22.64.77:8055/items/alert_db",headers=headers,json={"frame":response['id'],"camera_location":str(camera),"aadhaar_found":name}).json()
                        print(to_add)
                    print(name,face_distances)
                except Exception as e:
                    print(e,'HERE')


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
    op_buffer2 = multiprocessing.Queue()
    op_buffer3 = multiprocessing.Queue()

    with multiprocessing.Manager() as manager:

        exited = manager.Value('i',0)
        criminals_db = manager.dict()


        camera_reader = multiprocessing.Process(target=image_capture,args=(camera_feed_buffer,1,exited,op_buffer1))
        camera_reader.start()
        # camera_reader2 = multiprocessing.Process(target=image_capture,args=(camera_feed_buffer,2,exited,op_buffer2))
        # camera_reader2.start()
        # camera_reader3 = multiprocessing.Process(target=image_capture,args=(camera_feed_buffer,2,exited,op_buffer3))
        # camera_reader3.start()

        face_finder1 = multiprocessing.Process(target=find_face,args=(camera_feed_buffer,face_finder_buffer,exited))
        face_finder1.start()
        # face_finder2 = multiprocessing.Process(target=find_face,args=(camera_feed_buffer,face_finder_buffer,op_buffer,exited))
        # face_finder2.start()
        # face_finder3 = multiprocessing.Process(target=find_face,args=(camera_feed_buffer,face_finder_buffer,op_buffer,exited))
        # face_finder3.start()

        criminal_updater = multiprocessing.Process(target=get_criminal_encodings,args=(exited,criminals_db))
        criminal_updater.start()

        id_face_pro = multiprocessing.Process(target=id_face,args=(face_finder_buffer,exited,criminals_db))
        id_face_pro.start()

        while True:
            try:
                frame1,locations =  op_buffer1.get()
                # frame2,locations =  op_buffer2.get()
                # for i in locations:
                #     top,right,bottom,left = i
                #     crop = frame[top:bottom,left:right,::-1]
                cv2.imshow('Cam 1', cv2.resize(frame1[:,:,::-1],(480,270)))
                # cv2.imshow('Cam 2', frame2)
                # time.sleep(0.01)

            except Exception as e:
                print(e)
                pass

            # Hit 'q' on the keyboard to quit!
            if cv2.waitKey(1) & 0xFF == ord('q'):
                with exited.get_lock():
                    exited.value = 1
                camera_feed_buffer.close()
                face_finder_buffer.close()
                break
            time.sleep(0.01)

        camera_reader.kill()
        # camera_reader2.kill()
        # camera_reader3.kill()
        face_finder1.kill()
        # face_finder2.kill()
        # face_finder3.kill()
        criminal_updater.kill()
        id_face_pro.kill()

        camera_reader.join()
        # camera_reader2.join()
        # camera_reader3.join()
        face_finder1.join()
        # face_finder2.join()
        # face_finder3.join()
        criminal_updater.join()
        id_face_pro.join()
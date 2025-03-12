import math
from multiprocessing.managers import DictProxy, ValueProxy
import cv2
import multiprocessing
import face_recognition
import time
import numpy as np
import random
import requests
from datetime import timedelta,datetime

def image_capture(input_buffer:multiprocessing.Queue,camera:int,exited:ValueProxy,display_buffer:multiprocessing.Queue) -> None:
    video_capture = cv2.VideoCapture(camera)
    print("Width: %d, Height: %d, FPS: %d" % (video_capture.get(3), video_capture.get(4), video_capture.get(5)))

    while not exited.get():
        _, frame = video_capture.read()
        input_buffer.put((frame[:, :, ::-1],camera))
        display_buffer.put((frame[:, :, ::-1],camera))
        time.sleep(0.05) # For laptop webcam

    input_buffer.close()


def find_face(input_buffer:multiprocessing.Queue,output_buffer:multiprocessing.Queue,exited:ValueProxy) -> None: # type: ignore



    while not exited.get():
        rgb_frame,camera = input_buffer.get()
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)

        face_locations = face_recognition.face_locations(small_frame,1,model='cnn')
        face_encodings = face_recognition.face_encodings(small_frame, face_locations,model="large")

        try:

            for (top,right,bottom,left),encoding in zip(face_locations,face_encodings):
                output_buffer.put((rgb_frame,(top*4,right*4,bottom*4,left*4),encoding,camera))
        except:
            pass




        # time.sleep(0.01)
    output_buffer.close()


def id_face(input_buffer:multiprocessing.Queue,exited:ValueProxy,criminals_db:DictProxy): # type: ignore
    headers = {"Authorization": "Bearer 7k8V9rO8RtGRTYAeaN-NB2jVQ-DP9fzL"}
    direct_us_url = r'http://172.27.229.241:8055'
    

    found_cache = dict()
    diff = timedelta(seconds=10)
    
    while not exited.get():
        current_criminals_aadhaar = criminals_db.keys()
        temp = criminals_db.values()
        current_criminals_encodings = []
        user_types = []
        aadhaar_nos = []
        for encodings,user_type,aadhaar in temp:
            current_criminals_encodings.append(encodings)
            user_types.append(user_type)
            aadhaar_nos.append(aadhaar)
            


        frame,face_location,face_encoding,camera = input_buffer.get()
        
        flag = False
        
        if camera == 0:
            location_camera = "IIT"
        else:
            location_camera = "BIT"

        if len(current_criminals_encodings):
        # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(current_criminals_encodings, face_encoding,tolerance=0.4)
            name = "Unknown"

            # TODO : Upload to direct us - frame , face_location , time , camera - location
            face_distances = face_recognition.face_distance(current_criminals_encodings, face_encoding)

            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = current_criminals_aadhaar[best_match_index]
                sus_aadhaar = aadhaar_nos[best_match_index]
                current_date = datetime.now()
                if name in found_cache:
                    time_found = found_cache[name]
                    if current_date - time_found <= diff:
                        flag = False
                    else:
                        flag = True
                        found_cache[name] = datetime.now()
                else:
                    found_cache[name] = datetime.now()
                    flag = True

                try:
                    if flag:
                        flag = False
                        s =requests.Session()
                        top,right,bottom,left = face_location
                        crop = frame[top:bottom,left:right,::-1]
                        
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                        cv2.imwrite("frame.jpg",frame)
                        
                        
                        
                        
                        print(f"Found {name} - {user_types[best_match_index]}",time.ctime())
                        print("CRIMINAL")
                        print(sus_aadhaar)
                        
                        headers = {"Authorization": "Bearer 7k8V9rO8RtGRTYAeaN-NB2jVQ-DP9fzL"}
                        sus_aadhaar_details:dict = s.get(f"{direct_us_url}/items/aadhaar_db/{sus_aadhaar}",headers=headers).json()['data']
                        del sus_aadhaar_details['face_embedding']
                        
                        notes = "AADHAAR DETAILS FOUND !\n"
                        notes += f"NAME := {sus_aadhaar_details['name']} \n"
                        notes += f"ADDRESS := {sus_aadhaar_details['address']} \n"
                        notes += f"DOB := {sus_aadhaar_details['DOB']} \n"
                        notes += f"PHONE := {sus_aadhaar_details['phone_no']} \n"
                        
                    
                        with open("frame.jpg",'rb') as f:
                            response = s.post(f"{direct_us_url}/files",headers=headers,files={"file":("image.jpg", f, "image/jpeg")},data={"folder":"9ec2c9f6-3e72-432b-8173-5893fb3a63d2"}).json()['data']
                            print(response['id'])
                            to_add = s.post(f"{direct_us_url}/items/criminal_alert",headers=headers,json={"frame":response['id'],"location":location_camera,"criminal_detected":name,"suspect_aadhaar":sus_aadhaar,"aadhaar_notes":notes}).json()
                            print(to_add)
                        print(name,face_distances)
                except Exception as e:
                    print(e,'HERE')


def get_criminal_encodings(exited:ValueProxy,criminals_db:DictProxy):

    headers = {"Authorization": "Bearer 7k8V9rO8RtGRTYAeaN-NB2jVQ-DP9fzL"}
    direct_us_url = r'http://172.27.229.241:8055'
    

    while not exited.get():


        try:
            s = requests.Session()
            
            # Is a criminal
            criminals_aadhaar_full:list = s.get(f"{direct_us_url}/items/criminal_face",headers=headers).json()['data']
            criminals = []

            for elem in criminals_aadhaar_full:
                criminals.append(elem['id'])

            encodings = []
            aadhaar_nos = []
            
            
            for elem in criminals_aadhaar_full:
                encodings_full = elem['criminal_embedding']['data']
                aadhaar_nos.append(elem['probable_aadhaar'])
                encodings.append(encodings_full)

            to_share = {}

            for i in range(len(criminals)):
                to_share[criminals[i]] = [encodings[i],'criminal',aadhaar_nos[i]]
                
                
            criminals_db.clear()
            criminals_db.update(to_share)
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


        camera_reader = multiprocessing.Process(target=image_capture,args=(camera_feed_buffer,0,exited,op_buffer1))
        camera_reader.start()

        face_finder1 = multiprocessing.Process(target=find_face,args=(camera_feed_buffer,face_finder_buffer,exited))
        face_finder1.start()

        criminal_updater = multiprocessing.Process(target=get_criminal_encodings,args=(exited,criminals_db))
        criminal_updater.start()

        id_face_pro = multiprocessing.Process(target=id_face,args=(face_finder_buffer,exited,criminals_db))
        id_face_pro.start()

        while True:
            try:
                frame1,locations =  op_buffer1.get()
                cv2.imshow('Cam 1', frame1[:,:,::-1])

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
        face_finder1.kill()
        criminal_updater.kill()
        id_face_pro.kill()

        camera_reader.join()
        face_finder1.join()
        criminal_updater.join()
        id_face_pro.join()
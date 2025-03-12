import json
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
import urllib3
import winsound


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
    
    # Get data of criminals_with aadhaar
    
    
    while not exited.get():
        
        current_criminals_aadhaar = criminals_db.keys()
        temp = criminals_db.values()
        
        current_criminals_encodings = []
        current_criminals_aadhaar = []
        current_criminals_id = []
        
        current_missings_encodings = []
        current_missings_id = []
        
        
        
        for encodings,user_type,aadhaar,ids in temp:
            if user_type == 'criminal':
                current_criminals_encodings.append(encodings)
                current_criminals_aadhaar.append(aadhaar)
                current_criminals_id.append(ids)
            else:
                current_missings_id.append(ids)
                current_missings_encodings.append(encodings)
        
        # print(current_missings_encodings)
                
        frame,face_location,face_encoding,camera = input_buffer.get()
        
        if camera == 1:
            location_camera = "Bhopal"
        else:
            location_camera = "Chennai"
            
        location_camera = "LNCT"
            
        flag = False
        

        # Check if person is a CRIMINAL
        
        if len(current_criminals_encodings):
            matches = face_recognition.compare_faces(current_criminals_encodings, face_encoding,tolerance=0.4)
            name = "Unknown"

            # TODO : Upload to direct us - frame , face_location , time , camera - location
            face_distances = face_recognition.face_distance(current_criminals_encodings, face_encoding)

            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = current_criminals_id[best_match_index]
                sus_aadhaar = current_criminals_aadhaar[best_match_index]
                
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
                        winsound.Beep(3000,2000)
                        flag = False
                        s =requests.Session()
                        top,right,bottom,left = face_location
                        
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                        cv2.imwrite("frame.jpg",frame)
                        
                        print(f"Found {name} - CRIMINAL",time.ctime())
                    
                        headers = {"Authorization": "Bearer 7k8V9rO8RtGRTYAeaN-NB2jVQ-DP9fzL"}
                        sus_aadhaar_details:dict = s.get(f"{direct_us_url}/items/aadhaar_db/{sus_aadhaar}",headers=headers).json()['data']
                        del sus_aadhaar_details['face_embedding']
                        
                        notes = "AADHAAR DETAILS FOUND !\n"
                        notes += f"NAME := {sus_aadhaar_details['name']} \n"
                        notes += f"ADDRESS := {sus_aadhaar_details['address']} \n"
                        notes += f"DOB := {sus_aadhaar_details['DOB']} \n"
                        notes += f"PHONE := {sus_aadhaar_details['phone_no']} \n"
                        
                        email = sus_aadhaar_details['user_email']
                        
                        print(email)
                        
                        
                        
                        # res = s.post("https://f18f-2401-4900-7b3d-7b46-51cd-9b55-405c-cfff.ngrok-free.app/send-email",json={"email":email,"phone": "", "message": f"Criminal found - {name} "},headers = {"Content-Type": "application/json"},verify=False)
                        # print(res.text)
                        
                        # urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                        # url = "https://470d-2401-4900-7b3d-7b46-51cd-9b55-405c-cfff.ngrok-free.app/send-email"
                        # payload = {
                        #     "email": "amitrajegaonkar@gmail.com",
                        #     "message": f"Criminal Found - {name}"
                        # }
                        # headers1 = {"Content-Type": "application/json"}

                        # try:
                        #     res = requests.post(url, json=payload, headers=headers1, verify=False)  # 'verify=False' bypasses SSL
                        #     print("Response:", res.status_code, res.text)
                        # except requests.exceptions.RequestException as e:
                        #     print("An error occurred:",e)
                        
                    
                        with open("frame.jpg",'rb') as f:
                            response = s.post(f"{direct_us_url}/files",headers=headers,files={"file":("image.jpg", f, "image/jpeg")},data={"folder":"9ec2c9f6-3e72-432b-8173-5893fb3a63d2"}).json()['data']
                            print(response['id'])
                            to_add = s.post(f"{direct_us_url}/items/criminal_alert",headers=headers,json={"frame":response['id'],"location":location_camera,"criminal_detected":name,"suspect_aadhaar":sus_aadhaar,"aadhaar_notes":notes,'cctv_location':"POINT (77.5258 23.2481)"}).json()
                            
                            print(name,location_camera,"POINT (77.5 23.24)",time.ctime(),"CRIMINAL")
                            
                            
                        print(name,face_distances)
                except Exception as e:
                    print(e,'HERE')


        flag = False
        
        # Check if person is a MISSING
        
        if len(current_missings_encodings):
        # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(current_missings_encodings, face_encoding,tolerance=0.4)
            name = "Unknown"

            # TODO : Upload to direct us - frame , face_location , time , camera - location
            face_distances = face_recognition.face_distance(current_missings_encodings, face_encoding)

            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                
                name = current_missings_id[best_match_index]
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
                        winsound.Beep(6000,2000)
                        flag = False
                        s =requests.Session()
                        top,right,bottom,left = face_location
                        
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                        cv2.imwrite("frame.jpg",frame)
                        
                        print(f"Found {name} - MISSING",time.ctime())
                        print("MISSING")
                    
                        with open("frame.jpg",'rb') as f:
                            response = s.post(f"{direct_us_url}/files",headers=headers,files={"file":("image.jpg", f, "image/jpeg")},data={"folder":"9ec2c9f6-3e72-432b-8173-5893fb3a63d2"}).json()['data']
                            print(response['id'])
                            
                            to_add = s.post(f"{direct_us_url}/items/missing_alert",headers=headers,json={"frame":response['id'],"location":location_camera,"missing_detected":name,'cctv_location':"POINT (77.5258 23.2481)"}).json()
                            
                            print(name,time.ctime(),location_camera,"POINT (77.5258 23.2481)")
                        
                        print(name,face_distances)
                except Exception as e:
                    print(e,'HERE')


        

def get_criminal_encodings(exited:ValueProxy,criminals_db:DictProxy):
    
    


    headers = {"Authorization": "Bearer 7k8V9rO8RtGRTYAeaN-NB2jVQ-DP9fzL"}
    direct_us_url = r'http://172.27.229.241:8055'
    

    while not exited.get():

        # GET CRIMINAL ENCODINGS
        
        
        to_share = {}
        criminals_db.clear()
        
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


            for i in range(len(criminals)):
                to_share[f'{criminals[i]} - CRI'] = [encodings[i],'criminal',aadhaar_nos[i],criminals[i]]
                
                
        except Exception as e:
            print(e)

        
        
        try:
            s = requests.Session()
            
            # Is a criminal
            criminals_aadhaar_full:list = s.get(f"{direct_us_url}/items/missing_face",headers=headers).json()['data']
            criminals = []

            for elem in criminals_aadhaar_full:
                criminals.append(elem['id'])
                
                
            encodings = []
            for elem in criminals_aadhaar_full:
                encodings_full = elem['missing_embedding']['data']
                
                encodings.append(encodings_full)


            for i in range(len(criminals)):
                to_share[f'{criminals[i]} - MIS'] = [encodings[i],'missing',[],criminals[i]]
                
                
        except Exception as e:
            print(e,"LOLOL")

        criminals_db.update(to_share)
        with open('temp.json','w') as f:
            json.dump(to_share,f,indent=2)
        time.sleep(2)



if __name__ == '__main__':
    camera_feed_buffer = multiprocessing.Queue(20)
    face_finder_buffer = multiprocessing.Queue()
    op_buffer1 = multiprocessing.Queue()
    op_buffer2 = multiprocessing.Queue()

    with multiprocessing.Manager() as manager:

        exited = manager.Value('i',0)
        criminals_db = manager.dict()


        camera_reader = multiprocessing.Process(target=image_capture,args=(camera_feed_buffer,1,exited,op_buffer1))
        camera_reader.start()
        # camera_reader2 = multiprocessing.Process(target=image_capture,args=(camera_feed_buffer,1,exited,op_buffer2))
        # camera_reader2.start()

        face_finder1 = multiprocessing.Process(target=find_face,args=(camera_feed_buffer,face_finder_buffer,exited))
        face_finder1.start()

        criminal_updater = multiprocessing.Process(target=get_criminal_encodings,args=(exited,criminals_db))
        criminal_updater.start()

        id_face_pro = multiprocessing.Process(target=id_face,args=(face_finder_buffer,exited,criminals_db))
        id_face_pro.start()

        while True:
            try:
                frame1,locations =  op_buffer1.get()
                cv2.imshow('Cam 1', cv2.resize(frame1[:,:,::-1],(480,270)))
                # frame2,locations =  op_buffer2.get()
                # cv2.imshow('Cam 2', cv2.resize(frame2[:,:,::-1],(480,270)))
                

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
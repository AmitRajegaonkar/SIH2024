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

def id_face(input_buffer: multiprocessing.Queue, exited: ValueProxy, criminals_db: DictProxy) -> None:
    # Instead of fetching criminal encodings via API, we directly use the criminals_db (dictionary)
    while not exited.get():
        # Get the list of current criminal encodings and Aadhaar numbers
        current_criminals_aadhaar = list(criminals_db.keys())
        current_criminals_encodings = list(criminals_db.values())

        # Capture frame and face details
        frame, face_location, face_encoding, camera = input_buffer.get()
        print("Got a face, checking against criminal DB")

        if len(current_criminals_encodings):
            # Compare the captured face encoding with criminal encodings
            matches = face_recognition.compare_faces(current_criminals_encodings, face_encoding, tolerance=0.5)
            name = "Unknown"

            # Calculate face distances and find the best match
            face_distances = face_recognition.face_distance(current_criminals_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index]:
                name = current_criminals_aadhaar[best_match_index]
                print(f"Match found: {name} with distance: {face_distances[best_match_index]}")

                # Optional: Crop and save image (if you want to log it)
                top, right, bottom, left = face_location
                crop = frame[top:bottom, left:right, ::-1]
                cv2.imwrite(f"frame_{name}.jpg", crop)

                # You can add logging or further actions here, like updating logs, sending alerts, etc.
            else:
                print("No match found.")



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

        # Manually add some example criminal embeddings (for testing)
        # Add the new embedding as 128-dimensional
        criminals_db['new_criminal_aadhaar'] = [
        -0.14875316619873047,
        0.09818923473358154,
        0.08403059095144272,
        -0.1100567877292633,
        -0.16252639889717102,
        0.007132912520319223,
        -0.040293049067258835,
        -0.10438535362482071,
        0.22923456132411957,
        -0.20580452680587769,
        0.21533232927322388,
        0.04840946942567825,
        -0.2305605262517929,
        0.05308574438095093,
        -0.03242219239473343,
        0.18440663814544678,
        -0.20719578862190247,
        -0.18078498542308807,
        -0.07235647737979889,
        -0.07808547466993332,
        0.06788071990013123,
        -0.003341369330883026,
        -0.010379336774349213,
        0.09410283714532852,
        -0.08762581646442413,
        -0.36063456535339355,
        -0.09929068386554718,
        0.006987069267779589,
        -0.056629445403814316,
        -0.15948599576950073,
        0.1014762595295906,
        0.13268668949604034,
        -0.20296643674373627,
        0.04822801798582077,
        -0.02333485521376133,
        0.17293016612529755,
        -0.03779567778110504,
        -0.12059815227985382,
        0.09448686987161636,
        0.05464659631252289,
        -0.2692270576953888,
        0.001275984337553382,
        0.04040348902344704,
        0.26245638728141785,
        0.20429441332817078,
        -0.03413045406341553,
        0.04915850982069969,
        -0.07516375184059143,
        0.11804904043674469,
        -0.3380816876888275,
        0.07478287816047668,
        0.18009881675243378,
        0.076816126704216,
        0.07460950314998627,
        0.10649600625038147,
        -0.17913758754730225,
        0.07687597721815109,
        0.07097974419593811,
        -0.10805165022611618,
        0.050245363265275955,
        0.14897963404655457,
        -0.14973744750022888,
        0.0618743821978569,
        -0.040734224021434784,
        0.22365328669548035,
        0.14624296128749847,
        -0.14973893761634827,
        -0.148355171084404,
        0.1368539184331894,
        -0.15716378390789032,
        -0.08869849890470505,
        0.10224258154630661,
        -0.14164943993091583,
        -0.23161956667900085,
        -0.2664273679256439,
        0.05472634360194206,
        0.41822555661201477,
        0.1805887520313263,
        -0.12343229353427887,
        0.06640299409627914,
        -0.10617304593324661,
        0.002469001105055213,
        -0.015837067738175392,
        0.2746732234954834,
        0.012765147723257542,
        0.020269926637411118,
        -0.11908652633428574,
        0.08051030337810516,
        0.22525283694267273,
        0.028896186500787735,
        -0.04618856683373451,
        0.36386311054229736,
        0.002587719587609172,
        -0.019050780683755875,
        0.005479902029037476,
        0.08183516561985016,
        -0.09510727971792221,
        -0.02685762755572796,
        -0.08440040051937103,
        -0.03728362172842026,
        -0.07333207130432129,
        -0.042116206139326096,
        -0.10639292746782303,
        0.07533702254295349,
        -0.1782081127166748,
        0.2002885639667511,
        -0.1047796830534935,
        0.05117198824882507,
        -0.07135064899921417,
        -0.05572475865483284,
        -0.04056563600897789,
        0.004708400461822748,
        0.09759078174829483,
        -0.3092546761035919,
        0.15623903274536133,
        0.19928905367851257,
        0.04235149174928665,
        0.17282351851463318,
        0.06217816099524498,
        0.1066996231675148,
        0.06811624765396118,
        -0.1306104063987732,
        -0.1312454342842102,
        -0.02951616607606411,
        -0.013350357301533222,
        -0.05676491558551788,
        -0.04609686881303787,
        0.04315604642033577
    ]


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
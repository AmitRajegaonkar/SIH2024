# Face Recognition Project  

This project is a **face recognition system** using `dlib`, `face_recognition`, and `OpenCV`.  
It detects faces using the **HOG model** and extracts face encodings for recognition.

## 🚀 Installation  


## 📌 Notes  
- Ensure you have **Python 3.9.8** (as `dlib` has compatibility issues with newer versions).
- If installation fails, try:  
  ```sh
  pip install cmake dlib
  ```

### **1️⃣ Clone the Repository**  
```sh
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

### **2️⃣ Create and Activate Virtual Environment**  
```sh
python -m venv env
source env/Scripts/activate  # Windows
source env/bin/activate  # macOS/Linux
```

### **3️⃣ Install CMake and Build Tools**  
Before installing dependencies, install **CMake** through **Microsoft Visual Studio Code**:
1. Download and install **Visual Studio Build Tools** from [here](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
2. During installation, select **C++ build tools** and ensure the following components are checked:
   - **Windows 10 SDK**
   - **MSVC v142 - Visual C++ Build Tools**
   - **CMake**
3. Restart your system after installation.

Alternatively, install `cmake` via pip:
```sh
pip install cmake
```

### **4️⃣ Install Dependencies**  
```sh
pip install -r requirements.txt
```

## 🛠 Usage  
Run the face recognition script:  
```sh
python your_script.py
```

## 📜 Dependencies  
This project uses the following Python packages:  

- `certifi==2025.1.31`
- `charset-normalizer==3.4.1`
- `click==8.1.8`
- `cmake==3.31.6`
- `colorama==0.4.6`
- `dlib==19.24.6`
- `face-recognition==1.3.0`
- `face_recognition_models==0.3.0`
- `idna==3.10`
- `numpy==2.0.2`
- `opencv-python==4.11.0.86`
- `pillow==11.1.0`
- `requests==2.32.3`
- `urllib3==2.3.0`



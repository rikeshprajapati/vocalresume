import streamlit as st
import requests
import PyPDF2
from docx import Document
import os
import time
import google.generativeai as genai
import base64

# Configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set your imgBB API key directly here
imgbb_api_key = "2981b67226516503c32d117bdbdd3857"

# Function to save uploaded files
def save_uploaded_file(uploaded_file):
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    return file_path

# Function to upload image to imgBB and get public URL
def upload_to_imgbb(file_path, imgbb_api_key):
    url = "https://api.imgbb.com/1/upload"
    with open(file_path, "rb") as file:
        payload = {
            'key': imgbb_api_key,
            'image': base64.b64encode(file.read()).decode("utf-8")
        }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        response_json = response.json()
        if response_json['status'] == 200:
            return response_json['data']['url']
        else:
            st.error(f"Error uploading to imgBB: {response_json['error']['message']}")
            return None
    else:
        st.error(f"Error: {response.status_code} - {response.text}")
        return None

# Function to generate a brief introduction using Google Generative AI
def generate_introduction(model, resume_text):
    prompt = f"Generate a brief professional introduction based on the following resume. Highlight the key skills, include specific numbers and achievements from projects, and mention the total years of experience: {resume_text}"
    response = model.generate_content(prompt)
    return response.text

# Function to extract text from uploaded file
def extract_text_from_file(uploaded_file):
    file_type = uploaded_file.name.split('.')[-1]
    try:
        if file_type == 'pdf':
            reader = PyPDF2.PdfReader(uploaded_file)
            resume_text = ""
            for page in range(len(reader.pages)):
                resume_text += reader.pages[page].extract_text()
        elif file_type == 'docx':
            doc = Document(uploaded_file)
            resume_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return resume_text
    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return None

# Function to create a video using D-ID API
def text_to_video_did(text, source_url, d_id_api_key, voice_id):
    url = "https://api.d-id.com/talks"
    payload = {
        "script": {
            "type": "text",
            "input": text,
            "provider": {
                "type": "microsoft",
                "voice_id": voice_id
            }
        },
        "config": {
            "stitch": True,
            "result_format": "mp4", # Requesting a video in mp4 format
            "driver_expressions": {
                "expressions": [
                    {
                    "start_frame": 0,
                    "expression": "happy",
                    "intensity": 1
                    }
                ]
            }
        },
        "source_url": source_url
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {d_id_api_key}"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 201:
        video_id = response.json().get("id")
        video_status_url = f"https://api.d-id.com/talks/{video_id}"
        
        for _ in range(20):
            time.sleep(10)
            status_response = requests.get(video_status_url, headers=headers)
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] == "done":
                    return status_data["result_url"]
                elif status_data["status"] == "error":
                    st.error("Error in video generation")
                    return None
            else:
                st.error(f"Error checking status: {status_response.status_code}")
                return None
        
        st.error("Video generation timed out.")
        return None
    else:
        st.error(f"Error: {response.status_code} - {response.text}")
        return None

def main():
    st.title("VocalResume: AI Introduction Builder")

    # Description of the app
    st.write("""
    This Streamlit app allows you to generate a brief professional introduction 
    using the content from your resume.
    """)

    # Input for Google API Key and D-ID API Key
    st.write("[Click here to create a Google API Key](https://ai.google.dev/gemini-api/docs/api-key)")
    st.write("[Click here to create a D-ID Key](https://studio.d-id.com/account-settings)")
    google_api_key = st.text_input("Enter your Google API Key", type="password")
    d_id_api_key = st.text_input("Enter your D-ID API Key", type="password")

    if google_api_key:
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

    uploaded_file = st.file_uploader("Upload your resume", type=["pdf", "docx"])
    image_file = st.file_uploader("Upload your profile photo (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"])

    # Gender selection
    gender = st.radio("Select the gender:", ("Male", "Female"))

    # Determine the voice ID based on gender
    if gender == "Male":
        voice_id = "en-IN-PrabhatNeural"
    else:
        voice_id = "en-IN-NeerjaNeural"

    if image_file:
        file_path = save_uploaded_file(image_file)
        imgbb_url = upload_to_imgbb(file_path, imgbb_api_key)
        
        if imgbb_url:
            source_url = imgbb_url

    st.write("*Note:* The profile photo should be formal and align your body structure with your head.")

    if uploaded_file and google_api_key and d_id_api_key:
        resume_text = extract_text_from_file(uploaded_file)
        
        if resume_text:
            if st.button("Generate Introduction"):
                with st.spinner("Generating introduction..."):
                    introduction = generate_introduction(model, resume_text)
                
                if image_file:
                    with st.spinner("Creating video..."):
                        video_url = text_to_video_did(introduction, source_url, d_id_api_key, voice_id)
                    
                    if video_url:
                        st.write("*Introduction Video:*")
                        st.video(video_url)

if __name__ == "__main__":
    main()

from dotenv import load_dotenv

load_dotenv()
import os
import google.generativeai as genai
import pandas as pd
import docx2txt
import nltk 
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('punkt_tab')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
stop_words = set(stopwords.words('english'))
import re
from llama_index.core import SimpleDirectoryReader
import random
api_list = ["AIzaSyA51WTz0t69sBFs8D2ZmLLypKs6X9rIcEI","AIzaSyDlCk6V9XXwHEYJSjSC4-g28N69UgNcVYA"]
api_key=random.choices(api_list)
print(api_key[0])
genai.configure(api_key=api_key[0])
from flask import Flask, jsonify, request
import logging

app =Flask(__name__)

def preprocessing(document):
    text = document.replace('\n', ' ').replace('\t', ' ').lower()
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    tokens = word_tokenize(text)
    tokens = [re.sub(r'[^a-zA-Z\s]', '', token) for token in tokens]
    tokens = [token for token in tokens if token and token not in stop_words]
    preprocessed_text = ' '.join(tokens)
    return preprocessed_text


def get_gemini_response(input_text,prompt):
    model=genai.GenerativeModel('gemini-1.5-flash')
    response=model.generate_content([input_text,prompt],generation_config = genai.GenerationConfig(
        temperature=0.1
    ))
    return response.text

def input_pdf_setup(uploaded_file):
    if uploaded_file is not None:
        data = SimpleDirectoryReader(input_files=[uploaded_file]).load_data()
        data1 = " ".join([doc.text for doc in data])
        print("DATA",data1)
        document_resume = " ".join([doc.text.replace('\n', ' ').replace('\t', ' ').replace('\xa0', ' ') for doc in data])
        final = preprocessing(document_resume)
        return data1,final
    else:
        raise FileNotFoundError("No file uploaded")
    
Prompt = """Please extract the following information from the attached resume in the exact format provided below. 
Ensure the data is as it appears in the resume, and if certain details are not available, mark them as "Not Available".

Data=[
- Designation:
- Years of Experience(calculate it if not mentioned directly, only numeric number):
- Current Organization:

- Skills (List all relevant and valid skills mentioned. "," seperated):

- Education History (from oldest to latest):
    {NameInstitution: ,
    Degree: ,
    FieldStudy: ,
    Grade (if available): ,
    Start Year: , 
    End Year: ,
    Description (if available): ,}//n

- Professional Experience (from oldest to latest):
    {Company Name: ,
    Role/Title: ,
    Location: ,
    Employment Type (e.g., Full-time, Part-time, Internship): ,
    Start Date: , 
    End Date: ,
    Skills Used for this job: ,
    Description of Roles and Responsibilities: ,
    }//n

- First Name:
- Last Name:
- Current Location: 
]

"""

key_mapping_edu = {
    "Degree": "degree",
    "Description (if available)": "description",
    "Start Year": "startDate",
    "End Year": "endDate",
    "FieldStudy": "fieldOfStudy",
    "Grade (if available)": "grade",
    "NameInstitution": "institute"
}

key_mapping_prof = {"Company Name":"organization" ,
    "Role/Title":"designation" ,
    "Location":"location" ,
    "Employment Type (e.g., Full-time, Part-time, Internship)":"employmentType" ,
    "Start Date":"startDate" ,
    "End Date":"endDate" ,
    "Skills Used":"skillUsed" ,
    "Description of Roles and Responsibilities":"description",
    }

@app.route('/score_resumes', methods=['POST'])
def scoring():
    try:
        if 'resumes' not in request.files:
            return jsonify({'error': 'Please provide a JD file and at least one resume file.'}), 400

        resumes = request.files['resumes']
        print('resume',resumes)

        resume_folder_path = r'D:/Rohit/jdcv_score_app/jdcv_score_app/latest_gemini/temp5'
        os.makedirs(resume_folder_path, exist_ok=True)

        jd_file_path = os.path.join(resume_folder_path, resumes.filename)
        print('jd_file_path',jd_file_path)
        resumes.save(jd_file_path)
        
        # for i in resume_paths:
        data1,input_text = input_pdf_setup(jd_file_path)
        if input_text is None:
            return jsonify({'error': 'Error processing the JD file.'}), 500
        
        print(input_text)
        
        phone_pattern1 = re.compile(r'\+?\d{1,3}[-.\s]?\d{10}')
        phone_pattern2=re.compile(r'\+?\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}')
        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        social_media_pattern = re.compile(r'(https?://(?:www\.)?(?:linkedin|github|twitter|facebook|instagram)\.com/[^\s]+)')

        phone_numbers = phone_pattern1.findall(data1.replace("-",""))    
        print(phone_numbers)
        if not phone_numbers:
            phone_numbers = phone_pattern2.findall(data1)
        emails = email_pattern.findall(data1)
        emails=str(emails)
        social_media_links = social_media_pattern.findall(data1)
        social_media_links=list(social_media_links)
        valid_phone_numbers = [num for num in phone_numbers if 10 <= len(re.sub(r'\D', '', num)) <= 12]

        print(valid_phone_numbers)

        Country_code=''

        if len(valid_phone_numbers[0])==10:
            Country_code = ''
            valid_phone_numbers=valid_phone_numbers[0]
        elif len(valid_phone_numbers[0])>=12:
            Country_code = valid_phone_numbers[0][1:3]
            valid_phone_numbers=valid_phone_numbers[0][-10:]

        

        response = get_gemini_response(input_text,Prompt)
        
        t=response.split("\n-")
        print(type(t[5]))

        Designation = t[1].replace("Designation:","").replace('\n','')
        total_exp=t[2].replace("Years of Experience:","").replace('\n','')
        organization=t[3].replace("Current Organization:","").replace('\n','')
        skills=t[4].replace("Skills (List all relevant and valid skills mentioned):","").replace('\n','').replace("Skills:","")
        name=t[7].replace("First Name:","").replace('\n','').replace('[','').replace(']','')
        surname=t[8].replace("Last Name:","").replace('\n','').replace('[','').replace(']','')
        phone=str(valid_phone_numbers).replace('[','').replace(']','')
        country=Country_code.replace('[','').replace(']','')
        email=emails.replace('[','').replace(']','')
        social=social_media_links #.replace('[','').replace(']','')
        location=t[9].replace("Current Location:","").replace('\n','').replace('[','').replace(']','')

        educationHistory=t[5].replace("Education History (from oldest to latest):","").replace('\n','').replace('Education History:',"").replace("{","").replace("}","")
        edu=[element for element in educationHistory.split("//n") if len(element) > 0]
        final_edu=[]
        for i in edu:
            pairs = i.strip().split(',')
            result_dict={}
            for pair in pairs:
                if ':' in pair:  # Ensure there is a key-value pair to split
                    key, value = pair.split(":", 1)  # Split by the first occurrence of ":"
                    result_dict[key.strip()] = value.strip()
                    new_dict = {key_mapping_edu[key]: value for key, value in result_dict.items() if key in key_mapping_edu}
            final_edu.append(new_dict)
        
 
        professionalExperience=t[6].replace("Professional Experience (from oldest to latest):","").replace("{","").replace("}","").replace("Professional Experience:","")
        prof=[element for element in professionalExperience.split("//n") if len(element) > 0]
        final_prof=[]
        for i in prof:
            pairs = i.strip().split(',')
            result_dict={}
            for pair in pairs:
                if ':' in pair:  # Ensure there is a key-value pair to split
                    key, value = pair.split(":", 1)  # Split by the first occurrence of ":"
                    result_dict[key.strip()] = value.strip()
                    new_dict = {key_mapping_prof[key]: value for key, value in result_dict.items() if key in key_mapping_prof}
            final_prof.append(new_dict)

        final = {'designation':Designation,
                 'totalExperience':int(total_exp),
                 "organization":organization,
                 "SkillsInfo":skills,
                 'firstName':name,
                 'lastName':surname,
                 'phoneNo':int(phone),
                 "email":email,
                 "socialInfo":social,
                 "countryCode":int(country),
                 'location':location,
                 "educationHistory":final_edu, "professionalHistory":final_prof,"yearOfExperience":int(total_exp)}
        print(len(t))
        print(t)

        return final, 200

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5005)
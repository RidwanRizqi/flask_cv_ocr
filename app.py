import numpy
from flask import Flask, request, jsonify
import cv2
import pytesseract
import re

app = Flask(__name__)


def preprocess_text(text):
    # Hapus karakter aneh yang mungkin muncul di teks hasil OCR
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s.,]', '', text)
    return cleaned_text


def extract_section(text, section_start, section_end):
    section_start_upper = section_start.upper()
    section_end_upper = '|'.join([keyword.upper() for keyword in section_end]) if section_end else None

    # Menggunakan \b untuk memastikan kata kunci sebagai kata penuh
    # Hapus flag re.IGNORECASE untuk memastikan pencocokan kata kunci dalam UPPERCASE
    section_match = re.search(fr'\b{section_start_upper}\b\s*\n(.+?)(?:\b({section_end_upper})\b|\Z)', text,
                              re.DOTALL)
    return section_match.group(1).strip() if section_match else f"{section_start} section not found"


@app.route('/extract_info', methods=['POST'])
def extract_info():
    # Check if the POST request has the file part
    if 'file' not in request.files:
        return jsonify({"error": "No file part"})

    file = request.files['file']

    # Check if the file is empty
    if file.filename == '':
        return jsonify({"error": "No selected file"})

    # Read the image and perform OCR
    image = cv2.imdecode(numpy.fromstring(file.read(), numpy.uint8), cv2.IMREAD_UNCHANGED)

    # do preprocessing for image so can easily read by tesseract
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    invert = cv2.bitwise_not(thresh)
    kernel = numpy.ones((1, 1), numpy.uint8)
    dilated = cv2.dilate(invert, kernel, iterations=2)

    # save image to local
    cv2.imwrite("image.jpg", gray)
    cv2.imwrite("blur.jpg", blur)
    cv2.imwrite("thresh.jpg", thresh)
    cv2.imwrite("invert.jpg", invert)
    cv2.imwrite("dilated.jpg", dilated)

    text = pytesseract.image_to_string(dilated)

    # Extract information from the text
    # sections = text.split("\n\n")
    # teks = sections[0]
    teks = """Charles Bloomberg\n\nNew York City, New York 02 charlesbloomberggmail.com  01062375053 1 incbloomberg\n\n
    SKILLS\n
    Technical Skills Microsoft Suite, Google Suite, Windows, Linux\n\n
    Soft Skills Customer Service, Leadership, Teamwork, Data Management, Methodical Approach\n\n
    Fields of Interest Management, New Business Development, International Business\n
    SUMMARY\n\n
    Ahighly motivated and confident selfstarter, seeking to utilize acquired skills and education in an entrylevel IT position while contributing\ninnovative ideas to achieve professional growth and progress.\n\n
    EXPERIENCE\n\n
    Administrative Associate  Company A  New York City, NY  January 2018  Present\n\n 
    Organized and filed complex materials, operated mail storing and posting machinery with compliance with safety rules and regulations.\n\n 
    Coordinated shipping arrangements for facility, organized itineraries, handled hard copy and electronic correspondence, reports and memorandums\nof varying degrees and utilized Excel to construct and maintain data via spreadsheets.\n\nHVAC Technician  Company B  New York City, NY  August 2017  December 2017\n\n Applied focal HVAC codes ina piratical manner in order to Troubleshoot and repair HVAC systems and used technical prowess to interpret various\ntechnical data, such as pressure and temperature.\n\n 
    Layout, design, and install lowvoltage wiring.\n\n 
    Collaborates with sales and engineering to develop product definitions responsive to customer needs and market opportunities.\n\n
    Administrative Associate  Company C  New York City, NY  January 2016  August 2016\n\n 
    Organized and filed complex undefined materials such as archiving documents and sorted, processed, and delivered mail to correct recipient.\n\n 
    Operated mail storing and posting machinery with compliance with safety rules and regulations, regularly handled hard copy and electronic\ncorrespondence, reports and memorandums of varying degrees and utilized Excel to construct and maintain data via spreadsheets.\n\n Coordinated shipping arrangements for facility and organized itineraries. Guaranteed delivery of outgoing mail to post office inclusive of parcels and\ndomestic, intemational and thirdparty carries.\n\n
    Legal Document Archiver  Company D  New York City, NY  August 2014  December 2015\n\n 
    Operated various computer systems to preserve records of materials filled and removed, updating as necessary, and sorted and classified\ninformation according to company guidelines.\n\n 
    Maintained confidentiality of information in adherence to company policies and procedures and organized and filed complex undefined materials\nsuch as archiving documents which improved flow of office space by 50.\n\n
    CERTIFICATIONS\n\n
    Google IT Support Professional Certificate  Coursera  2019\n Certified in knowing how to provide endtoend customer support, ranging from identifying problems to troubleshooting and debugging.\n\n
    COURSEWORK\n\n
    Technical Support Fundamentals  Coursera\n Learned how to utilize common problemsolving methodologies and soft skills in an Information Technology setting.\n\n
    The Bits and Bytes of Computer Networking  Coursera\n Learned computer networks in terms of the fivelayer model. understand all of the standard protocols involved with TCPIP communications\n\n
    Operating Systems and You Becoming a Power User  Coursera\n Learned how to perform critical tasks like managing software and users, and configuring hardware.\n\n
    System Administration and IT Infrastructure Services  Coursera\n Learned how to manage and configure servers and how to use industry tools to manage computers, user information, and user productivity.\n\n
    IT Security Defense against the digital dark arts  Coursera\n Learned how to evaluate potential risk and recommend ways to reduce risk. Best practices for securing a network. And how to help others to grasp\nsecurity concepts and protect themselves.\n\n
    EDUCATION\n
    HVAC Certification  Lincoln Technical Institute of Technology  New York City, NY  2014\n\n
    """

    name_match = re.search(r'^([^\n]+)', teks)
    name = name_match.group(1).strip() if name_match else "Name not found"

    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', teks)
    email = email_match.group() if email_match else "Email not found"

    phone_match = re.search(r'\b\d{10,}\b', teks)
    phone = phone_match.group() if phone_match else "Phone number not found"

    # Preprocess the text before extracting sections
    teks = preprocess_text(teks)

    # Keyword sections
    section_keywords = ["SUMMARY", "EXPERIENCE", "CERTIFICATIONS", "COURSEWORK", "EDUCATION", "SKILLS"]

    # Extract text from each section
    sections_data = {}
    for i in range(len(section_keywords)):
        section_start = section_keywords[i]
        # end section berisi seluruh keyword
        section_end = section_keywords
        section_text = extract_section(teks, section_start, section_end)
        sections_data[section_start] = section_text

    result = {
        "Name": name,
        "Email": email,
        "Phone": phone,
        "Sections": sections_data
    }

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)

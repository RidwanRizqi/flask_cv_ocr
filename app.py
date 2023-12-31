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
    teks = text

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

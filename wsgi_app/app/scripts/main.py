import os.path
import subprocess
import sys
import csv
import time
import uuid
import pytesseract
import re
from PIL import Image
from dotenv import load_dotenv
import logging

session_uuid = uuid.uuid4()


logging.basicConfig(filename=str(session_uuid)+"-session.log", filemode="w")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
load_dotenv("../../.env")

data_dir = os.path.join(os.getcwd(), '../data')


def write_csv(extracted_value):
    global session_uuid, data_dir
    timestamp = time.time()

    os.makedirs(data_dir, exist_ok=True)
    csv_file = os.path.join(data_dir, 'results.csv')
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, str(session_uuid), extracted_value])


def extract_values():
    fieldnames = ['timestamp', 'session_uuid', 'extracted_value']
    re_pattern = r"#\d+\,\d+#"

    pytesseract.pytesseract.tesseract_cmd = os.environ.get('TESSERACT_CMD')
    pytesseract.pytesseract.tessdata_dir_config = os.environ.get('TESSERACT_TESSDATA_CONFIG')

    matches = []
    data_dir = os.path.join(os.getcwd(), "../data")

    # Iterate through the data directory and extract numeric values from PDF files
    for file_ in os.listdir(data_dir):
        if file_.endswith(".pdf"):
            pdf_file = os.path.join(data_dir, file_)
            png_file = os.path.join(data_dir, os.path.splitext(file_)[0] + ".png")
            gs_path = r"C:\\Program Files\\gs\\gs10.00.0\\bin\\gswin64.exe"

            # Convert PDF to PNG using Ghostscript
            gs_args = [
                gs_path, "-dNOSAFER", "-dQUIET", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m",
                "-r300", "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
                "-sOutputFile={}".format(png_file), pdf_file
            ]
            gs_process = subprocess.Popen(gs_args)
            gs_process.communicate()

            # Read text from PNG using Tesseract
            image = Image.open(png_file)
            text = pytesseract.image_to_string(image)

            # Extract numeric characters and commas
            numeric_matches = re.findall(re_pattern, text)
            if numeric_matches:
                extracted_value = numeric_matches[0]
            else:
                extracted_value = ""

            # Generate timestamp and session UUID
            timestamp = time.time()

            csv_file = os.path.join(data_dir, "results.csv")
            filemode = "a" if os.path.isfile(csv_file) else "w"

            # Save results to CSV file

            with open(csv_file, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                if filemode == "w":
                    writer.writeheader()
                else:
                    with open(csv_file) as csv_file_tmp:
                        content_tmp = csv_file_tmp.read()
                        if len(content_tmp.strip()) == 0:
                            f.close()
                            csv_file_tmp.close()
                            print(csv_file)
                            os.remove(csv_file)

                writer.writerow({
                    "timestamp": timestamp,
                    "session_uuid": session_uuid,
                    "extracted_value": extracted_value
                })

            matches.append(extracted_value)

            image = Image.open(png_file)

            text = pytesseract.image_to_string(image)
            numeric_matches = re.findall(re_pattern, text)
            return numeric_matches
    return matches


if __name__ == '__main__':
    filemode = "a"
    if not os.path.isfile("results.txt"):
        filemode = "w"

    with open("results.txt", filemode) as results_f:
        for item_i in range(0, 50):
            txt_ = (str(item_i)+" ")
            vals = extract_values()
            txt_ += str(vals)
            logger.debug(txt_)
            results_f.write(txt_)
        results_f.close()


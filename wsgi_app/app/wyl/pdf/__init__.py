import base64
import csv
import io
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
import zlib
from datetime import datetime
import pytesseract
from PIL import Image as PILImage
from PyPDF2 import PdfReader, PdfWriter
from wand.image import Image
from wsgi_app.app.config import WindowsConfig, ProductionConfig
from wsgi_app.app.wyl.utils import clean_dict

is_win = platform.platform().lower().startswith("win")
if is_win:
    current_config = WindowsConfig
else:
    current_config = ProductionConfig

data_dir = os.path.join(current_config.PROJECT_LOCATION, "app", "data")


def write_csv(extracted_value, session_uuid):
    global data_dir
    timestamp = time.time()

    os.makedirs(data_dir, exist_ok=True)
    csv_file = os.path.join(data_dir, 'results.csv')
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, str(session_uuid), extracted_value])


class Extractor:
    fieldnames = ['timestamp', 'filename', 'extracted_value']
    re_pattern = r"#\d+\,\d+#"
    data_dir = None

    def __init__(self):
        self.tessdata_config = os.environ.get('TESSERACT_TESSDATA_CONFIG')
        if pytesseract.pytesseract.tesseract_cmd != os.environ.get('TESSERACT_CMD'):
            self.tesseract_cmd = os.environ.get('TESSERACT_CMD')
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        target_location = os.path.join(current_config.PROJECT_LOCATION, "app", "target")
        self.data_dir = target_location if os.path.isdir(target_location) else data_dir
        self.matches = []
        self.red_files = []
        self.green_files = []

        self.numeric_matches_d = {}
        self.processed_files = []
        self.current_file = None
        self.png_files = []
        self.collect_png_files()
        super().__init__()

    def collect_png_files(self):
        for file_ in os.listdir(data_dir):
            if file_.endswith(".png"):
                png_file = os.path.join(self.data_dir, file_)
                self.png_files.append(png_file)

    def process_png_files(self):
        for file_path in self.png_files:
            self.process_png(file_path)

    results = {}
    
    def process_png(self, file_path):
        logging.debug("processing: {}".format(os.path.basename(file_path)))
        image = PILImage.open(file_path)
        text = pytesseract.image_to_string(image)

        # Extract numeric characters and commas
        numeric_matches = re.findall(self.re_pattern, text)
        if numeric_matches:
            if len(numeric_matches) == 1:
                extracted_value = numeric_matches[0]
            else:
                extracted_values = []
                for current_item_i in range(0, len(numeric_matches)):

                    extracted_values.append(numeric_matches[current_item_i])
                extracted_value = ",".join(extracted_values)
        else:
            extracted_value = ""
        if len(extracted_value) > 0:
            self.results[file_path] = extracted_value


def extract_values(session_uuid):
    global data_dir
    fieldnames = ['timestamp', 'filename', 'extracted_value']
    re_pattern = r"#\d+\,\d+#"

    pytesseract.pytesseract.tesseract_cmd = os.environ.get('TESSERACT_CMD')
    pytesseract.pytesseract.tessdata_dir_config = os.environ.get('TESSERACT_TESSDATA_CONFIG')
    target_location = os.path.join(current_config.PROJECT_LOCATION, "app", "target")
    data_dir = target_location if os.path.isdir(target_location) else data_dir
    matches = []
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    red_files = []
    green_files = []

    numeric_matches_d = {}
    if len(os.listdir(data_dir)) > 0:
        for file_ in os.listdir(data_dir):
            if file_.endswith(".png"):
                png_file = os.path.join(data_dir, file_)
                # print(file_)
                image = PILImage.open(png_file)
                text = pytesseract.image_to_string(image)

                # Extract numeric characters and commas
                numeric_matches = re.findall(re_pattern, text)
                if numeric_matches:
                    extracted_value = numeric_matches[0]
                else:
                    extracted_value = ""

                # Generate timestamp and session UUID
                timestamp = time.time()

                csv_file = os.path.join(data_dir, "results-{}.csv".format(session_uuid))
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

                                os.remove(csv_file)

                    writer.writerow({
                        "timestamp": timestamp,
                        'filename': file_,
                        "extracted_value": extracted_value
                    })

                matches.append(extracted_value)

                image = PILImage.open(png_file)

                text = pytesseract.image_to_string(image)
                numeric_matches = re.findall(re_pattern, text)
                if numeric_matches is not None:
                    if len(numeric_matches) > 0:
                        if file_ not in numeric_matches_d:
                            numeric_matches_d[file_] = []
                        for item_i in range(0, len(numeric_matches)):
                            print("val: {}".format(numeric_matches[item_i]))
                            numeric_matches_d[file_].append(numeric_matches[item_i])
                        green_files.append(file_)
                else:
                    red_files.append(file_)
    data_dict = {
        "red": red_files,
        "dir": data_dir,
        "files": os.listdir(data_dir),
        "uuid": session_uuid,
        "matches": matches,
        "matches_d": numeric_matches_d
    }
    with open(os.path.join(data_dir, "current-results-"+session_uuid+".json"), "w") as json_result_f:
        json_result_f.write(json.dumps(data_dict, indent=4))
        json_result_f.close()
    return data_dict


class PDFManager:
    results = {}
    session_filename = None
    source_folder: str = None
    target_folder: str = None
    socketio = None
    console_handler = None
    file_handler = None
    logger = None

    def __init__(self, current_socketio):
        self.current_config = current_config
        self.socketio = current_socketio
        self.source_folder = os.path.join(
            self.current_config.PROJECT_LOCATION, "app", self.current_config.source_foldername
        )
        self.target_folder = os.path.join(
            self.current_config.PROJECT_LOCATION, "app", self.current_config.target_foldername
        )
        self.session_filename = "session-" + \
                                str(uuid.uuid4()) + \
                                "-" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + \
                                ".b64"

        pytesseract.pytesseract.tesseract_cmd = self.current_config.TESSERACT_CMD

        logging.debug("source folder: {}".format(self.source_folder))
        logging.debug("TESS: " + self.current_config.TESSERACT_CMD)

        self.logger = self.get_logger(
            __name__,
            log_filepath=os.path.join(
                self.current_config.PROJECT_LOCATION,
                self.current_config.logs_foldername,
                self.session_filename.rstrip(".b64") +
                ".log"
            )
        )

        if not os.path.isdir(self.source_folder):
            print("NO SOURCE FOLDER EXISTS")
            print(self.source_folder)
            if not os.path.exists(self.source_folder):
                os.makedirs(self.source_folder)

        # Create the target and PNG folders if they don't exist
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)
        if self.socketio is not None:
            if hasattr(self.socketio, 'emit'):
                try:
                    self.socketio.emit('my_response',
                                       {'data': 'Init event'},
                                       namespace='/')
                except AttributeError as e:
                    print(str(e))
                    print("attr")
        else:
            self.logger.debug("PDF MANAGER INITIALIZED")
        super().__init__()

    def get_console_handler(self):
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setFormatter(self.current_config.FORMATTER)
        return self.console_handler

    def get_file_handler(self, current_logfile):
        self.file_handler = logging.FileHandler(current_logfile, mode="a")
        self.file_handler.setFormatter(self.current_config.FORMATTER)
        return self.file_handler

    def get_logger(self, logger_name, log_filepath):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)  # better to have too much log than not enough
        self.logger.addHandler(self.get_console_handler())
        self.logger.addHandler(self.get_file_handler(log_filepath))
        # with this pattern, it's rarely necessary to propagate the error up to parent
        self.logger.propagate = False
        return self.logger

    def run(self):
        self.extract_pages()
        self.convert_to_png()
        self.socketio.emit("my_response", {"data": "run: DETECTING UPSIDE-DOWN OCR"})
        self.logger.debug("DETECTING UPSIDE-DOWN OCR")
        # self.inspect_upsidedown()

        """
        for file in os.listdir(self.target_folder):
            print("removing: {}".format(file))
            self.socketio.emit("my_response", {"data": "removing: {}".format(file)})
            try:
                self.logger.debug("DEL: removing: {}".format(file))

                os.remove(os.path.join(self.target_folder, file))
            except OSError:
                pass
        """

        self.socketio.emit("my_response", {"data": "writing results: {}".format(self.session_filename)})

        json_str = json.dumps(
            clean_dict(
                self.results
            )
        )
        for line in json_str.splitlines():
            self.socketio.emit("my_response", {"data": "result-line: {}".format(line)})

        with open(os.path.join(
                self.current_config.PROJECT_LOCATION, self.current_config.sessions_foldername, self.session_filename
        ), "wb") as current_session_file:
            current_session_file.write(
                base64.b64encode(
                    zlib.compress(
                        json.dumps(
                            clean_dict(
                                self.results
                            )
                        ).encode("utf-8")
                    )
                )
            )
            current_session_file.close()

    def detect_upsidedown(self, input_path, lang=None, pytesseract_parameters=None):
        self.socketio.emit('my_response',
                           {'data': "DETECT-UPSIDEDOWN: {}".format(os.path.basename(input_path))},
                           namespace='/')
        params = "--psm 6"
        params += " " + os.environ.get('TESSERACT_TESSDATA_CONFIG')
        if lang is None:
            lang = "ell"
        if pytesseract_parameters is not None:
            params += pytesseract_parameters

        input_filetype = "pdf"

        if os.path.basename(input_path).endswith("png"):
            input_filetype = "png"
            with open(input_path, 'rb') as f:
                img = PILImage.open(f)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')

        else:
            with Image(filename=input_path, resolution=300) as img:
                img.format = 'png'
                img_blob = img.make_blob()
                img_buffer = io.BytesIO(img_blob)

        if os.path.basename(input_path) not in self.results.keys():
            self.results[os.path.basename(input_path)] = {}

        # input_path
        img_filename = os.path.basename(input_path)
        self.results[img_filename]["pil_img"] = PILImage.open(img_buffer)
        self.results[img_filename]["pil_img_rotated"] = self.results[img_filename]["pil_img"].rotate(180)

        self.results[img_filename]["text"] = pytesseract.image_to_string(
            self.results[img_filename]["pil_img"], lang=lang, config=params
        )

        self.results[img_filename]["text_2"] = pytesseract.image_to_string(
            self.results[img_filename]["pil_img_rotated"], lang='ell', config=params)

        self.results[img_filename]["lines"] = self.results[img_filename]["text"].split('\n')
        self.results[img_filename]["lines_2"] = self.results[img_filename]["text_2"].split('\n')

        self.logger.debug("DETECT-UPSIDEDOWN: call {}".format(
            "pytesseract.image_to_string(pil_img, lang='" + lang + "', config='" + params + "')"))

        self.logger.debug("DETECT-UPSIDEDOWN: lines: {}".format(len(self.results[img_filename]["lines"])))

        self.logger.debug("DETECT-UPSIDEDOWN: lines-inverted: {}".format(len(self.results[img_filename]["lines_2"])))

        self.results[img_filename]["line_orientations"] = []
        for line in self.results[img_filename]["lines"]:
            line_length = len(line.strip())
            if line_length > 0:
                line_orientation = abs(line.count(' ') / line_length - 0.5)
                self.results[img_filename]["line_orientations"].append(line_orientation)

        self.results[img_filename]["mean_orientation"] = sum(self.results[img_filename]["line_orientations"]) / len(
            self.results[img_filename]["line_orientations"])

        self.logger.debug("DETECT-UPSIDEDOWN: mean_orientation: {}".format(
            self.results[img_filename]["mean_orientation"]))
        self.socketio.emit('my_response',
                           {'data': "DETECT-UPSIDEDOWN: mean_orientation: {}".format(
                               self.results[img_filename]["mean_orientation"])},
                           namespace='/')
        self.results[img_filename]["line_orientations_2"] = []
        for line in self.results[img_filename]["lines_2"]:
            line_length = len(line.strip())
            if line_length > 0:
                line_orientation = abs(line.count(' ') / line_length - 0.5)
                self.results[img_filename]["line_orientations_2"].append(line_orientation)

        self.results[img_filename]["mean_orientation_2"] = sum(self.results[img_filename]["line_orientations_2"]) / len(
            self.results[img_filename]["line_orientations_2"])

        self.logger.debug("DETECT-UPSIDEDOWN: mean_orientation-inverted: {}".format(
            self.results[img_filename]["mean_orientation_2"]))

        diff = self.results[img_filename]["mean_orientation"] - self.results[img_filename]["mean_orientation_2"]

        readable = True
        if diff < 0:
            readable = False

        self.logger.debug(
            'DETECT-UPSIDEDOWN: orientation {} file: {} path: {}'.format(str(readable), input_filetype, input_path))

        with open(
                os.path.join(
                    os.path.dirname(input_path),
                    os.path.basename(input_path).rstrip(".pdf") + "_A.txt"
                ), encoding="utf-8", mode="w") as txt_file_a:
            txt_file_a.write("\n".join(self.results[img_filename]["lines"]))
            txt_file_a.close()

        with open(
                os.path.join(
                    os.path.dirname(input_path),
                    os.path.basename(input_path).rstrip(".pdf") + "_B.txt"),
                encoding="utf-8", mode="w") as txt_file_b:
            txt_file_b.write("\n".join(self.results[img_filename]["lines_2"]))
            txt_file_b.close()

        # logger.debug("DETECT-UPSIDEDOWN: content:")
        # logger.debug("DETECT-UPSIDEDOWN: {}".format("\n".join(lines)))
        # logger.debug("DETECT-UPSIDEDOWN: \ncontent:")
        # logger.debug("DETECT-UPSIDEDOWN: {}".format("\n".join(lines_2)))
        # logger.debug("DETECT-UPSIDEDOWN: -----")

    def extract_pages(self):
        for filename in os.listdir(self.source_folder):
            if filename.endswith('.pdf'):
                self.logger.debug("EXTRACT-PAGES: processing file: {}".format(filename))
                self.socketio.emit('my_response',
                                   {'data': "EXTRACT-PAGES: processing file: {}".format(filename)},
                                   namespace='/')
                source_path = os.path.join(self.source_folder, filename)
                with open(source_path, 'rb') as source_file:
                    pdf_reader = PdfReader(source_file)
                    num_pages = len(pdf_reader.pages)

                    if num_pages == 1:
                        # If the file has only one page, copy the file to the target directory
                        target_path = os.path.join(self.target_folder, filename)
                        self.logger.debug("EXTRACT-PAGES: single page: {}".format(os.path.basename(source_path)))

                        shutil.copyfile(source_path, target_path)
                        self.logger.debug("EXTRACT-PAGES: copied to : {}".format(target_path))
                    else:
                        self.logger.debug("EXTRACT-PAGES: multiple pages: {}".format(os.path.basename(source_path)))
                        self.socketio.emit('my_response',
                                           {'data': "EXTRACT-PAGES: multiple pages: {}".format(num_pages)},
                                           namespace='/')
                        # Split the PDF into separate pages and save each page as a separate file
                        for page_num in range(num_pages):
                            page = pdf_reader.pages[page_num]
                            pdf_writer = PdfWriter()
                            self.logger.debug("EXTRACT-PAGES: adding page: {}".format(page_num))
                            self.socketio.emit('my_response',
                                               {'data': "EXTRACT-PAGES: adding page: {}".format(page_num)},
                                               namespace='/')
                            pdf_writer.add_page(page)

                            target_filename = f"{os.path.splitext(filename)[0]}_page{page_num + 1}.pdf"
                            target_path = os.path.join(self.target_folder, target_filename)
                            self.logger.debug("EXTRACT-PAGES: target_path: {}".format(target_path))

                            # Create any missing directories in the target path logger.debug("EXTRACT-PAGES: os.makedirs
                            # if not exists: {}".format(os.path.dirname(target_path)))
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)

                            with open(target_path, 'wb') as target_file:
                                self.logger.debug("EXTRACT-PAGES: save single page to: {}".format(target_file))
                                pdf_writer.write(target_file)

    def convert_to_png_(self):
        # Convert the PDF files in the target folder to PNG images and save them in the same directory
        for filename in os.listdir(self.target_folder):
            if filename.endswith('.pdf'):
                self.logger.debug("CONVERT-PDF-PNG: processing: {}".format(filename))
                self.socketio.emit('my_response',
                                   {'data': "CONVERT-PDF-PNG: processing: {}".format(filename)},
                                   namespace='/')
                source_path = os.path.join(self.target_folder, filename)
                with Image(filename=source_path) as img:
                    png_filename = f"{os.path.splitext(filename)[0]}.png"
                    png_path = os.path.join(self.target_folder, png_filename)
                    self.logger.debug("CONVERT-PDF-PNG: save converted to: {}".format(png_path))
                    self.socketio.emit('my_response',
                                       {'data': "CONVERT-PDF-PNG: save converted to: {}".format(png_path)},
                                       namespace='/')
                    img.save(filename=png_path)

    @staticmethod
    def convert_pdf_to_png(pdf_path, output_folder):
        gs_path = r"C:\Program Files\gs\gs10.00.0\bin\gswin64c.exe"
        filename = os.path.basename(pdf_path)
        args = [
            gs_path,  # path to Ghostscript executable
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=png16m",
            "-r300",
            f"-sOutputFile={output_folder}\\{filename}_page_%03d.png",
            pdf_path
        ]
        subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def convert_to_png(self):
        for filename in os.listdir(self.target_folder):
            if filename.endswith('.pdf'):
                pdf_path = os.path.join(self.target_folder, filename)
                self.socketio.emit('my_response',
                                   {'data': "CONVERT-PDF-PNG: processing: {}".format(filename)},
                                   namespace='/')

                # convert_pdf_to_png(pdf_path, output_folder)
                output_filename = f"{pdf_path[:-4]}.png"
                png_path = os.path.join(self.target_folder, output_filename)
                print(png_path)
                self.convert_pdf_to_png(pdf_path, os.path.dirname(png_path))
                """
                pages = convert_from_path(pdf_path)
                for i, page in enumerate(pages):
                    output_filename = f"{pdf_path[:-4]}.png"
                    png_path = os.path.join(self.target_folder, output_filename)
                    self.socketio.emit('my_response',
                                       {'data': "CONVERT-PDF-PNG: save converted to: {}".format(png_path)},
                                       namespace='/')
                    self.logger.debug("CONVERT-PDF-PNG: save converted to: {}".format(png_path))
                    page.save(png_path, 'PNG')
                """

    def inspect_upsidedown(self):
        self.socketio.emit('my_response',
                           {'data': "DIR: {}".format(self.target_folder)},
                           namespace='/')
        self.logger.debug("DIR: {}".format(self.target_folder))
        self.logger.debug("DETECT-UPSIDEDOWN: processing directory: {}".format(os.listdir(self.target_folder)))
        self.socketio.emit('my_response',
                           {'data': "DETECT-UPSIDEDOWN: processing directory: {}".format(
                               os.listdir(self.target_folder))},
                           namespace='/')
        for filename in os.listdir(self.target_folder):
            if filename.endswith('.png'):
                self.logger.debug("DETECT-UPSIDEDOWN: call: {}".format(
                    "detect_upsidedown('{}')".format(os.path.basename(os.path.join(self.target_folder, filename)))))
                self.detect_upsidedown(os.path.join(self.target_folder, filename), lang="ell")

                # numeric only
                # , pytesseract_parameters="--oem 0
                # -c tessedit_char_whitelist=0123456789"

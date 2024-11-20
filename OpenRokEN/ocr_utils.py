import pytesseract
import cv2
import json

# Carregar as configurações (config.json)
with open("config.json") as config_file:
    config = json.load(config_file)

# Definir o caminho do Tesseract PATH
pytesseract.pytesseract.tesseract_cmd = config["tesseract_path"]

def capture_text_from_area(image, x1, x2, y1, y2):
    height, width = image.shape[:2]
    x_start, x_end = int(x1 * width), int(x2 * width)
    y_start, y_end = int(y1 * height), int(y2 * height)
    cropped_image = image[y_start:y_end, x_start:x_end]
    text = pytesseract.image_to_string(cropped_image)
    return text

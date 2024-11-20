import cv2
import numpy as np
import pyautogui

def selecionar_area():
    screenshot = pyautogui.screenshot()
    image = np.array(screenshot)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    roi = cv2.selectROI("Selecione a área", image, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow("Selecione a área")
    x, y, w, h = roi
    return x, y, x + w, y + h

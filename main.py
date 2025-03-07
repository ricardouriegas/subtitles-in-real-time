import cv2
import numpy as np
import speech_recognition as sr
from queue import Queue

# Configuración inicial
text_queue = Queue()
current_text = ""
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 200

def audio_callback(recognizer, audio):
    """Callback para procesamiento de audio en segundo plano"""
    try:
        text = recognizer.recognize_google(audio, language='es-ES')
        text_queue.put(text)
    except sr.UnknownValueError:
        text_queue.put("")
    except sr.RequestError:
        text_queue.put("Error de conexión")

def create_transparent_window():
    """Crea una ventana transparente con texto"""
    window = np.zeros((WINDOW_HEIGHT, WINDOW_WIDTH, 4), dtype=np.uint8)
    return window

def update_subtitles(frame, text):
    """Actualiza los subtítulos en la ventana"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    thickness = 2
    color = (255, 255, 255, 255)  # Blanco con opacidad completa
    
    # Calcula el tamaño del texto
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    
    # Posición centrada
    text_x = (WINDOW_WIDTH - text_size[0]) // 2
    text_y = (WINDOW_HEIGHT + text_size[1]) // 2
    
    # Añade texto
    cv2.putText(frame, text, (text_x, text_y), font, 
                font_scale, color, thickness, cv2.LINE_AA)
    return frame

# Configurar reconocedor de voz
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# Ajustar para ruido ambiente y iniciar escucha en segundo plano
with microphone as source:
    recognizer.adjust_for_ambient_noise(source)

stop_listening = recognizer.listen_in_background(
    microphone, 
    audio_callback,
    phrase_time_limit=1  # Límite de tiempo por frase
)

# Crear ventana de subtítulos
cv2.namedWindow('Subtítulos', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Subtítulos', WINDOW_WIDTH, WINDOW_HEIGHT)

try:
    while True:
        # Actualizar texto
        if not text_queue.empty():
            new_text = text_queue.get()
            current_text = new_text if new_text else current_text
        
        # Crear frame transparente
        frame = create_transparent_window()
        
        # Actualizar subtítulos
        frame = update_subtitles(frame, current_text)
        
        # Mostrar frame
        cv2.imshow('Subtítulos', frame)
        
        # Salir con 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    stop_listening(wait_for_stop=False)
    cv2.destroyAllWindows()
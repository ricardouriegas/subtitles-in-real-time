import cv2
import numpy as np
import speech_recognition as sr
from queue import Queue
import os
import subprocess

# Configuración inicial
text_queue = Queue()
current_text = ""
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600  # Increased height for camera feed
is_recording = False
video_writer = None
recorded_frames = []

def audio_callback(recognizer, audio):
    """Callback para procesamiento de audio en segundo plano"""
    try:
        text = recognizer.recognize_google(audio, language='es-ES')
        text_queue.put(text)
    except sr.UnknownValueError:
        text_queue.put("")
    except sr.RequestError:
        text_queue.put("Error de conexión")

def overlay_subtitles(frame, text):
    """Superpone subtítulos en la parte inferior del frame"""
    if not text:
        return frame
    
    # Configuración de fuente
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    thickness = 2
    color = (255, 255, 255)  # Texto blanco
    
    # Calcular tamaño del texto para centrarlo
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = (frame.shape[1] - text_size[0]) // 2
    text_y = frame.shape[0] - 30  # Posición cerca de la parte inferior
    
    # Crear rectángulo semi-transparente para mejor legibilidad
    overlay = frame.copy()
    cv2.rectangle(overlay, 
                 (0, text_y - text_size[1] - 10),
                 (frame.shape[1], frame.shape[0]),
                 (0, 0, 0), -1)
    
    # Aplicar transparencia
    alpha = 0.6
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    
    # Añadir texto
    cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    return frame

def start_recording(frame):
    """Inicia la grabación de video"""
    global is_recording, recorded_frames
    is_recording = True
    recorded_frames = [frame.copy()]  # Iniciar con el frame actual
    print("Grabación iniciada. Presiona 'r' nuevamente para detener y guardar.")

def stop_recording_and_save():
    """Detiene la grabación y abre diálogo para guardar usando zenity"""
    global is_recording, recorded_frames
    
    if not recorded_frames:
        print("No hay frames grabados para guardar")
        is_recording = False
        return
    
    # Usar zenity para mostrar el diálogo de guardar archivo
    try:
        # Ejecutar el comando zenity
        result = subprocess.run([
            'zenity', '--file-selection', 
            '--save', 
            '--confirm-overwrite',
            '--title=Guardar video con subtítulos',
            '--file-filter=*.avi',
            '--filename=video_subtitulado.avi'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:  # Usuario canceló el diálogo
            print("Guardado cancelado")
            is_recording = False
            recorded_frames = []
            return
            
        file_path = result.stdout.strip()
        
        # Asegurar que tenga extensión .avi
        if not file_path.endswith('.avi'):
            file_path += '.avi'
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Configurar VideoWriter
        height, width = recorded_frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(file_path, fourcc, 20.0, (width, height))
        
        # Escribir frames
        print(f"Guardando {len(recorded_frames)} frames en {file_path}")
        for frame in recorded_frames:
            out.write(frame)
        
        # Liberar recursos
        out.release()
        print(f"Video guardado correctamente en: {file_path}")
        
    except FileNotFoundError:
        # Zenity no está instalado, usar un nombre de archivo predeterminado
        print("Zenity no está instalado. Guardando con nombre predeterminado.")
        
        home_dir = os.path.expanduser("~")
        default_path = os.path.join(home_dir, "Videos", "video_subtitulado.avi")
        os.makedirs(os.path.dirname(default_path), exist_ok=True)
        
        # Configurar VideoWriter con ruta predeterminada
        height, width = recorded_frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(default_path, fourcc, 20.0, (width, height))
        
        # Escribir frames
        for frame in recorded_frames:
            out.write(frame)
            
        # Liberar recursos
        out.release()
        print(f"Video guardado en: {default_path}")
    
    is_recording = False
    recorded_frames = []

# Inicializar la cámara
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: No se pudo abrir la cámara.")
    exit()

# Configurar reconocedor de voz
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# Ajustar para ruido ambiente y iniciar escucha en segundo plano
with microphone as source:
    print("Ajustando para ruido ambiente...")
    recognizer.adjust_for_ambient_noise(source)
    print("Listo para escuchar!")

stop_listening = recognizer.listen_in_background(
    microphone, 
    audio_callback,
    phrase_time_limit=2  # Límite de tiempo por frase ligeramente mayor
)

# Crear ventana para la visualización
cv2.namedWindow('Subtitulador en tiempo real', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Subtitulador en tiempo real', WINDOW_WIDTH, WINDOW_HEIGHT)
print("Presiona 'r' para iniciar/detener la grabación. Presiona 'q' para salir.")

try:
    while True:
        # Capturar frame de la cámara
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar el frame")
            break
        
        # Redimensionar frame si es necesario
        frame = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # Actualizar texto de subtítulos
        if not text_queue.empty():
            new_text = text_queue.get()
            if new_text:  # Solo actualizar si hay texto nuevo
                current_text = new_text
        
        # Superponer subtítulos
        display_frame = overlay_subtitles(frame.copy(), current_text)
        
        # Mostrar indicador de grabación si está activo
        if is_recording:
            # Añadir círculo rojo en esquina superior derecha
            cv2.circle(display_frame, (display_frame.shape[1] - 20, 20), 10, (0, 0, 255), -1)
            # Guardar el frame con los subtítulos
            recorded_frames.append(display_frame.copy())
        
        # Mostrar frame con subtítulos
        cv2.imshow('Subtitulador en tiempo real', display_frame)
        
        # Comprobar teclas
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Salir con 'q'
            break
        elif key == ord('r'):  # Iniciar/detener grabación con 'r'
            if is_recording:
                stop_recording_and_save()
            else:
                start_recording(display_frame)

finally:
    # Liberar recursos
    stop_listening(wait_for_stop=False)
    cap.release()
    cv2.destroyAllWindows()
    print("Subtitulador cerrado correctamente")
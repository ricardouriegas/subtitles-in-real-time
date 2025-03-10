import cv2
import numpy as np
import speech_recognition as sr # OK
from queue import Queue
import os
import subprocess
import tempfile
import pyaudio # OK
import wave
import threading
import time # OK
from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import Qt
import sys

# Configuración inicial
text_queue = Queue()
current_text = ""
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
is_recording = False
video_writer = None
recorded_frames = []
frame_timestamps = []  # Almacenar timestamps para cada frame

# Configuración de audio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
audio_frames = []
audio_thread = None

# Inicializar QApplication para PyQt6
app = QApplication.instance() or QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)  # evitar que la app se cierre al cerrar diálogos

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

def record_audio():
    """Graba audio en segundo plano mientras se graba el video"""
    global audio_frames, is_recording
    
    p = pyaudio.PyAudio()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    while is_recording:
        data = stream.read(CHUNK)
        audio_frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()

def start_recording(frame):
    """Inicia la grabación de video y audio"""
    global is_recording, recorded_frames, audio_frames, audio_thread, frame_timestamps
    
    is_recording = True
    recorded_frames = [frame.copy()]
    frame_timestamps = [time.time()]  # Registrar timestamp del primer frame
    audio_frames = []
    
    # Iniciar grabación de audio en un hilo separado
    audio_thread = threading.Thread(target=record_audio)
    audio_thread.start()

def stop_recording_and_save():
    """Detiene la grabación y abre diálogo para guardar usando PyQt6"""
    global is_recording, recorded_frames, audio_frames, audio_thread, frame_timestamps
    
    # Detener la grabación
    is_recording = False
    
    if not recorded_frames:
        print("No hay frames grabados para guardar")
        return
    
    # Esperar a que termine el hilo de audio
    if audio_thread:
        audio_thread.join()
    
    # Usar PyQt6 para mostrar el diálogo de guardar archivo
    file_path, _ = QFileDialog.getSaveFileName(
        None,
        "Guardar video con subtítulos",
        os.path.expanduser("~/Videos/video_subtitulado.mp4"),
        "Videos (*.mp4)",
        options=QFileDialog.Option.DontUseNativeDialog
    )
    
    if not file_path:  # Usuario canceló el diálogo
        print("Guardado cancelado")
        recorded_frames = []
        audio_frames = []
        frame_timestamps = []
        return
        
    # Asegurar que tenga extensión .mp4
    if not file_path.endswith('.mp4'):
        file_path += '.mp4'
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Calcular el FPS real basado en timestamps
    if len(frame_timestamps) > 1:
        duration = frame_timestamps[-1] - frame_timestamps[0]
        real_fps = (len(frame_timestamps) - 1) / duration
    else:
        real_fps = 15.0  # Valor por defecto si no hay suficientes frames
    
    # Crear archivos temporales para video y audio
    with tempfile.NamedTemporaryFile(suffix='.avi', delete=False) as temp_video_file, \
         tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
        
        temp_video_path = temp_video_file.name
        temp_audio_path = temp_audio_file.name
    
    # Guardar video temporal con FPS calculado
    height, width = recorded_frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(temp_video_path, fourcc, real_fps, (width, height))
    
    for frame in recorded_frames:
        out.write(frame)
    
    out.release()
    
    # Guardar audio temporal si hay frames de audio
    if audio_frames:
        wf = wave.open(temp_audio_path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(audio_frames))
        wf.close()
        
        # Combinar audio y video con ffmpeg, configurando explícitamente el FPS
        try:
            subprocess.run([
                'ffmpeg', '-y',
                '-r', f'{real_fps}',  # Especificar FPS de entrada
                '-i', temp_video_path,
                '-i', temp_audio_path,
                '-c:v', 'libx264',
                '-r', f'{real_fps}',  # Mantener el mismo FPS para la salida
                '-c:a', 'aac',
                '-strict', 'experimental',
                '-map', '0:v:0',  # Mapear video del primer archivo
                '-map', '1:a:0',  # Mapear audio del segundo archivo
                '-shortest',  # Usar la duración del stream más corto
                file_path
            ], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error al combinar audio y video. FFmpeg puede no estar instalado.")
            print(f"Los archivos temporales estan en:\nVideo: {temp_video_path}\nAudio: {temp_audio_path}")
            return
    else:
        # Si no hay audio, usar ffmpeg para convertir el video a MP4
        try:
            subprocess.run([
                'ffmpeg', '-y',
                '-r', f'{real_fps}',
                '-i', temp_video_path,
                '-c:v', 'libx264',
                '-r', f'{real_fps}',
                file_path
            ], check=True)
            print(f"Video (sin audio) guardado en: {file_path}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Si ffmpeg falla, simplemente copiar el archivo
            os.rename(temp_video_path, file_path)
            print(f"Video (sin audio) guardado en: {file_path}")
    
    # Limpiar archivos temporales
    try:
        os.unlink(temp_video_path)
        if audio_frames:
            os.unlink(temp_audio_path)
    except:
        pass
    
    recorded_frames = []
    audio_frames = []
    frame_timestamps = []

# Inicializar la cámara
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("No se pudo abrir la camara.")
    exit()

# Configurar reconocedor de voz
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# Ajustar para ruido ambiente y iniciar escucha en segundo plano
with microphone as source:
    recognizer.adjust_for_ambient_noise(source)

stop_listening = recognizer.listen_in_background(
    microphone, 
    audio_callback,
    phrase_time_limit=2  # Límite de tiempo por frase ligeramente mayor
)

# Crear ventana para la visualización
cv2.namedWindow('Subtitulador en tiempo real', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Subtitulador en tiempo real', WINDOW_WIDTH, WINDOW_HEIGHT)

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
            # Registrar timestamp para este frame
            frame_timestamps.append(time.time())
        
        # Mostrar frame con subtítulos
        cv2.imshow('Subtitulador en tiempo real', display_frame)
        
        # Comprobar teclas
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Salir con 'q'
            break
        elif key == ord('r'):  # Iniciar/detener grabación con 'r'
            if is_recording:
                stop_recording_and_save()
                app.processEvents()  # Asegurar que la GUI de Qt se actualice
            else:
                start_recording(display_frame)

finally:
    # Liberar recursos
    stop_listening(wait_for_stop=False)
    cap.release()
    cv2.destroyAllWindows()
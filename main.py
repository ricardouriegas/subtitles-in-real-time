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
from PIL import Image, ImageDraw, ImageFont  # Added for Unicode text support
from datetime import datetime, timedelta

# Configuración inicial
text_queue = Queue()
current_text = ""
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
is_recording = False
video_writer = None
recorded_frames = []
clean_frames = []  # Frames sin subtítulos
frame_timestamps = []  # Almacenar timestamps para cada frame
subtitle_data = []  # Lista para almacenar datos de subtítulos (texto, tiempo inicio, tiempo fin)

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
        text_queue.put((text, time.time()))  # Añadir timestamp junto con el texto
    except sr.UnknownValueError:
        text_queue.put(("", time.time()))
    except sr.RequestError:
        text_queue.put(("Error de conexión", time.time()))

def overlay_subtitles(frame, text):
    """Superpone subtítulos en la parte inferior del frame con soporte para caracteres Unicode"""
    if not text:
        return frame
    
    # Convertir frame de OpenCV a formato PIL
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(pil_image)
    
    # Intentar cargar una fuente que soporte Unicode
    try:
        # Intenta usar fuentes del sistema que probablemente soporten caracteres Unicode
        font_size = 36
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        try:
            # Alternativa en Linux
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except IOError:
            # Si no se puede cargar ninguna fuente, usar la predeterminada
            font = ImageFont.load_default()
    
    # Calcular tamaño del texto para centrarlo
    text_width, text_height = draw.textsize(text, font=font) if hasattr(draw, 'textsize') else draw.textbbox((0, 0), text, font=font)[2:4]
    
    # Posicionar texto centrado en la parte inferior
    text_x = (frame.shape[1] - text_width) // 2
    text_y = frame.shape[0] - text_height - 30  # Posición cerca de la parte inferior
    
    # Crear rectángulo semi-transparente para mejor legibilidad
    overlay = frame.copy()
    cv2.rectangle(overlay, 
                 (0, text_y - 10),
                 (frame.shape[1], frame.shape[0]),
                 (0, 0, 0), -1)
    
    # Aplicar transparencia
    alpha = 0.6
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    
    # Convertir de nuevo el frame modificado a PIL
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(pil_image)
    
    # Dibujar el texto con PIL (soporta Unicode)
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))
    
    # Convertir de vuelta a formato OpenCV
    result_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    return result_frame

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

def generate_srt_file(subtitle_data, output_path):
    """Genera un archivo SRT a partir de los datos de subtítulos"""
    if not subtitle_data:
        return False
    
    # Ordenar datos de subtítulos por tiempo de inicio
    subtitle_data.sort(key=lambda x: x[1])
    
    with open(output_path, 'w', encoding='utf-8') as srt_file:
        for i, (text, start_time, end_time) in enumerate(subtitle_data, 1):
            if not text:  # Ignorar entradas sin texto
                continue
                
            # Convertir timestamps a formato SRT (HH:MM:SS,mmm)
            start_timestamp = datetime.utcfromtimestamp(start_time - frame_timestamps[0])
            end_timestamp = datetime.utcfromtimestamp(end_time - frame_timestamps[0])
            
            start_str = start_timestamp.strftime('%H:%M:%S,%f')[:12]  # Formato HH:MM:SS,mmm
            end_str = end_timestamp.strftime('%H:%M:%S,%f')[:12]      # Formato HH:MM:SS,mmm
            
            # Escribir entrada de subtítulo
            srt_file.write(f"{i}\n")
            srt_file.write(f"{start_str} --> {end_str}\n")
            srt_file.write(f"{text}\n\n")
    
    return True

def start_recording(frame):
    """Inicia la grabación de video y audio"""
    global is_recording, recorded_frames, clean_frames, audio_frames, audio_thread, frame_timestamps, subtitle_data
    
    is_recording = True
    recorded_frames = [frame.copy()]
    clean_frames = [frame.copy()]  # También guardamos frames sin subtítulos
    frame_timestamps = [time.time()]  # Registrar timestamp del primer frame
    audio_frames = []
    subtitle_data = []  # Reiniciar datos de subtítulos
    
    # Iniciar grabación de audio en un hilo separado
    audio_thread = threading.Thread(target=record_audio)
    audio_thread.start()

def stop_recording_and_save():
    """Detiene la grabación y abre diálogo para guardar usando PyQt6"""
    global is_recording, recorded_frames, clean_frames, audio_frames, audio_thread, frame_timestamps, subtitle_data
    
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
        clean_frames = []
        audio_frames = []
        frame_timestamps = []
        subtitle_data = []
        return
        
    # Asegurar que tenga extensión .mp4
    if not file_path.endswith('.mp4'):
        file_path += '.mp4'
    
    # Definir rutas para los archivos adicionales
    base_path = file_path[:-4]  # Eliminar extensión .mp4
    clean_video_path = f"{base_path}_clean.mp4"
    srt_path = f"{base_path}.srt"
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Calcular el FPS real basado en timestamps
    if len(frame_timestamps) > 1:
        duration = frame_timestamps[-1] - frame_timestamps[0]
        real_fps = (len(frame_timestamps) - 1) / duration
    else:
        real_fps = 15.0  # Valor por defecto si no hay suficientes frames
    
    # Crear archivos temporales para video con subtítulos, video limpio y audio
    with tempfile.NamedTemporaryFile(suffix='.avi', delete=False) as temp_video_file, \
         tempfile.NamedTemporaryFile(suffix='.avi', delete=False) as temp_clean_video_file, \
         tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
        
        temp_video_path = temp_video_file.name
        temp_clean_video_path = temp_clean_video_file.name
        temp_audio_path = temp_audio_file.name
    
    # Guardar video temporal con subtítulos
    height, width = recorded_frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(temp_video_path, fourcc, real_fps, (width, height))
    
    for frame in recorded_frames:
        out.write(frame)
    
    out.release()
    
    # Guardar video temporal sin subtítulos
    out_clean = cv2.VideoWriter(temp_clean_video_path, fourcc, real_fps, (width, height))
    
    for frame in clean_frames:
        out_clean.write(frame)
    
    out_clean.release()
    
    # Guardar audio temporal si hay frames de audio
    if audio_frames:
        wf = wave.open(temp_audio_path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(audio_frames))
        wf.close()
        
        # Generar archivo SRT con los subtítulos
        if subtitle_data:
            generate_srt_file(subtitle_data, srt_path)
            print(f"Archivo SRT generado: {srt_path}")
        
        # Combinar audio y video con subtítulos
        try:
            subprocess.run([
                'ffmpeg', '-y',
                '-r', f'{real_fps}',
                '-i', temp_video_path,
                '-i', temp_audio_path,
                '-c:v', 'libx264',
                '-r', f'{real_fps}',
                '-c:a', 'aac',
                '-strict', 'experimental',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                file_path
            ], check=True)
            print(f"Video con subtítulos guardado en: {file_path}")
            
            # Combinar audio y video limpio (sin subtítulos)
            subprocess.run([
                'ffmpeg', '-y',
                '-r', f'{real_fps}',
                '-i', temp_clean_video_path,
                '-i', temp_audio_path,
                '-c:v', 'libx264',
                '-r', f'{real_fps}',
                '-c:a', 'aac',
                '-strict', 'experimental',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                clean_video_path
            ], check=True)
            print(f"Video limpio (sin subtítulos) guardado en: {clean_video_path}")
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error al combinar audio y video. FFmpeg puede no estar instalado.")
            print(f"Los archivos temporales están en:\nVideo: {temp_video_path}\nVideo limpio: {temp_clean_video_path}\nAudio: {temp_audio_path}")
            return
    else:
        # Si no hay audio, usar ffmpeg para convertir los videos a MP4
        try:
            subprocess.run([
                'ffmpeg', '-y',
                '-r', f'{real_fps}',
                '-i', temp_video_path,
                '-c:v', 'libx264',
                '-r', f'{real_fps}',
                file_path
            ], check=True)
            
            subprocess.run([
                'ffmpeg', '-y',
                '-r', f'{real_fps}',
                '-i', temp_clean_video_path,
                '-c:v', 'libx264',
                '-r', f'{real_fps}',
                clean_video_path
            ], check=True)
            
            print(f"Videos guardados en:\nCon subtítulos: {file_path}\nSin subtítulos: {clean_video_path}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Si ffmpeg falla, simplemente copiar los archivos
            os.rename(temp_video_path, file_path)
            os.rename(temp_clean_video_path, clean_video_path)
            print(f"Videos guardados en:\nCon subtítulos: {file_path}\nSin subtítulos: {clean_video_path}")
    
    # Limpiar archivos temporales
    try:
        os.unlink(temp_video_path)
        os.unlink(temp_clean_video_path)
        if audio_frames:
            os.unlink(temp_audio_path)
    except:
        pass
    
    recorded_frames = []
    clean_frames = []
    audio_frames = []
    frame_timestamps = []
    subtitle_data = []

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
    phrase_time_limit=12  # Límite de tiempo por frase ligeramente mayor
)

# Crear ventana para la visualización
cv2.namedWindow('Subtitulador en tiempo real', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Subtitulador en tiempo real', WINDOW_WIDTH, WINDOW_HEIGHT)

try:
    last_subtitle_time = 0
    current_subtitle_start = 0
    last_text = ""
    
    while True:
        # Capturar frame de la cámara
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar el frame")
            break
        
        # Redimensionar frame si es necesario
        frame = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # Frame limpio para grabar sin subtítulos
        clean_frame = frame.copy()
        
        # Actualizar texto de subtítulos
        if not text_queue.empty():
            new_text, timestamp = text_queue.get()
            
            if new_text and new_text != last_text:  # Nuevo texto diferente
                current_time = timestamp
                
                # Si hay un subtítulo previo, registrarlo con su tiempo de fin
                if last_text and is_recording and last_subtitle_time > 0:
                    subtitle_data.append((last_text, current_subtitle_start, current_time))
                
                # Registrar inicio del nuevo subtítulo
                current_subtitle_start = current_time
                current_text = new_text
                last_text = new_text
                last_subtitle_time = current_time
        
        # Superponer subtítulos
        display_frame = overlay_subtitles(frame.copy(), current_text)
        
        # Mostrar indicador de grabación si está activo
        if is_recording:
            # Añadir círculo rojo en esquina superior derecha
            cv2.circle(display_frame, (display_frame.shape[1] - 20, 20), 10, (0, 0, 255), -1)
            # Guardar el frame con subtítulos y el frame limpio
            recorded_frames.append(display_frame.copy())
            clean_frames.append(clean_frame.copy())
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
                # Añadir el último subtítulo si existe
                if last_text and last_subtitle_time > 0:
                    subtitle_data.append((last_text, current_subtitle_start, time.time()))
                stop_recording_and_save()
                app.processEvents()  # Asegurar que la GUI de Qt se actualice
            else:
                start_recording(frame)

finally:
    # Liberar recursos
    stop_listening(wait_for_stop=False)
    cap.release()
    cv2.destroyAllWindows()
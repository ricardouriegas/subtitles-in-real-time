# Grabador de Video con Subtítulos

Este programa graba video desde la webcam mientras genera subtítulos a partir del micrófono utilizando reconocimiento de voz en español.

## Requisitos

Para ejecutar este script, necesitarás instalar las siguientes dependencias:

```bash
pip install numpy scikit-learn mediapipe opencv-python SpeechRecognition pyaudio
```

También necesitarás instalar portaudio19:

```bash
# En sistemas basados en Debian/Ubuntu
sudo apt-get install portaudio19-dev
```

## Cómo usar

1. Ejecuta el script: `python grabador_subtitulos.py`
2. El programa comenzará a grabar video desde tu webcam y a generar subtítulos a partir de tu micrófono
3. Habla claramente para una mejor generación de subtítulos
4. Presiona 'q' para detener la grabación
5. Se te pedirá que ingreses una ruta donde guardar el video final
6. El programa guardará tanto el video como un archivo SRT con los subtítulos

## Características

- Grabación de video con subtítulos en tiempo real
- Reconocimiento de voz en español
- Los subtítulos se muestran directamente en el video mientras grabas
- Se guarda un archivo SRT separado para usar con herramientas externas

## Incrustación de subtítulos con mejor calidad

El programa guarda un video con subtítulos básicos y un archivo SRT separado. Para incrustar los subtítulos con mejor calidad, puedes usar ffmpeg manualmente:

```bash
ffmpeg -i video_grabado.mp4 -vf "subtitles=video_grabado.srt:force_style=FontName='LiberationSans-Regular,PrimaryColour=&H0000FF00'" video_final.mp4
```

Este comando creará un nuevo video con subtítulos en verde y una mejor apariencia.

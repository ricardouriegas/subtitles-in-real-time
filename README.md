# Grabador de Video con Subtítulos

Este programa es capaz de grabar un video usando la webcam mientras genera subtítulos en español a partir del micrófono.

## Requisitos

Para ejecutar `main.py`, necesitarás instalar las siguientes dependencias:

<!-- TODO: agregar las dependencias que faltan -->

```bash
pip install numpy opencv-python SpeechRecognition pyaudio
```

También necesitarás instalar portaudio:

```bash
# Debian/Ubuntu
sudo apt-get install portaudio19-dev

# Fedora
sudo dnf install portaudio-devel

```

## Cómo usar

1. Ejecuta el script: `python main.py`
2. La aplicación comenzará a subtitular mientras muestra tu webcam
3. Presiona 'r' para iniciar o detener la grabación
4. Se te pedirá que ingreses una ruta donde guardar el video final
5. El programa guardará tanto el video como un archivo SRT con los subtítulos
6. Presiona 'q' para detener por completo la aplicación

## Características

- Grabación de video con subtítulos en tiempo real
- Reconocimiento de voz en **español**
- Los subtítulos se muestran directamente en el video mientras grabas
- Se guarda un archivo SRT separado para usar con herramientas externas

<!-- ## Incrustación de subtítulos con mejor calidad

El programa guarda un video con subtítulos básicos y un archivo SRT separado. Para incrustar los subtítulos con mejor calidad, puedes usar ffmpeg manualmente:

```bash
ffmpeg -i video_grabado.mp4 -vf "subtitles=video_grabado.srt:force_style=FontName='LiberationSans-Regular,PrimaryColour=&H0000FF00'" video_final.mp4
```

Este comando creará un nuevo video con subtítulos en verde y una mejor apariencia. -->

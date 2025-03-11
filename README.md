# Grabador de Video con Subtítulos

Este programa es capaz de grabar un video usando la webcam mientras genera subtítulos en español a partir del micrófono.

## Requisitos

Para ejecutar `main.py`, necesitarás instalar las siguientes dependencias:

<!-- TODO: agregar las dependencias que faltan -->

```bash
pip install numpy opencv-python SpeechRecognition pyaudio
```

También necesitarás instalar `portaudio` y `ffmpeg`:

```bash
# Debian/Ubuntu
sudo apt-get install portaudio19-dev ffmpeg

# Fedora
sudo dnf install portaudio-devel ffmpeg

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
- Reconocimiento de voz _español_
- Los subtítulos se muestran directamente en el video mientras grabas
- Se guarda un archivo SRT separado para usar con herramientas externas

## Resultados

El programa guarda un video con subtítulos básicos, un video sin subtítulos y un archivo SRT.

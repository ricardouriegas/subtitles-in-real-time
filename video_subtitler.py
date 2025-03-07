import cv2
import time
import speech_recognition as sr
import threading
import os
import tempfile
import subprocess
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timedelta

class VideoSubtitler:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_running = False
        self.video_capture = None
        self.audio_thread = None
        self.subtitles = []
        self.temp_dir = tempfile.mkdtemp()
        self.temp_video = os.path.join(self.temp_dir, "temp_video.mp4")
        self.temp_srt = os.path.join(self.temp_dir, "temp_subtitles.srt")
        self.start_time = None
        self.video_writer = None
        self.frame_width = 640
        self.frame_height = 480
        self.fps = 30.0

    def start_recording(self):
        self.video_capture = cv2.VideoCapture(0)
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(
            self.temp_video, fourcc, self.fps, 
            (self.frame_width, self.frame_height)
        )
        
        self.is_running = True
        self.start_time = datetime.now()
        self.audio_thread = threading.Thread(target=self.process_audio)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        
        self.record_video()

    def process_audio(self):
        subtitle_count = 1
        
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
            while self.is_running:
                try:
                    print("Listening...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    
                    current_time = datetime.now() - self.start_time
                    start_time_str = str(timedelta(seconds=int(current_time.total_seconds())))
                    
                    try:
                        text = self.recognizer.recognize_google(audio)
                        print(f"Subtitle: {text}")
                        
                        end_time = datetime.now() - self.start_time
                        end_time_str = str(timedelta(seconds=int(end_time.total_seconds())))
                        
                        self.subtitles.append({
                            'number': subtitle_count,
                            'start': start_time_str,
                            'end': end_time_str,
                            'text': text
                        })
                        
                        subtitle_count += 1
                        
                    except sr.UnknownValueError:
                        print("Could not understand audio")
                    except sr.RequestError as e:
                        print(f"Could not request results; {e}")
                        
                except Exception as e:
                    print(f"Error in audio processing: {e}")
    
    def record_video(self):
        try:
            current_subtitle_idx = 0
            current_subtitle_text = ""
            
            while self.is_running:
                ret, frame = self.video_capture.read()
                if not ret:
                    break
                    
                # Show current subtitle on frame
                if self.subtitles and current_subtitle_idx < len(self.subtitles):
                    current_subtitle_text = self.subtitles[current_subtitle_idx]['text']
                    
                if current_subtitle_text:
                    # Add subtitle text to the video frame
                    text_size = cv2.getTextSize(current_subtitle_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                    text_x = (frame.shape[1] - text_size[0]) // 2
                    text_y = frame.shape[0] - 30
                    cv2.putText(frame, current_subtitle_text, 
                                (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                                (255, 255, 255), 2, cv2.LINE_AA)
                
                # Save frame to video file
                self.video_writer.write(frame)
                
                # Display the frame
                cv2.imshow('Video with Subtitles', frame)
                
                # Update current subtitle index
                if self.subtitles:
                    current_subtitle_idx = min(len(self.subtitles) - 1, current_subtitle_idx + 1)
                
                # Exit on 'q' press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.is_running = False
                    
        finally:
            self.cleanup()
    
    def write_srt_file(self):
        with open(self.temp_srt, 'w') as f:
            for subtitle in self.subtitles:
                f.write(f"{subtitle['number']}\n")
                f.write(f"{subtitle['start'].replace('.', ',')} --> {subtitle['end'].replace('.', ',')}\n")
                f.write(f"{subtitle['text']}\n\n")
    
    def save_final_video(self):
        # Create a Tkinter root window
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        
        # Show the save file dialog
        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")],
            title="Save Video with Subtitles"
        )
        
        if output_path:
            # Write the subtitles to SRT file
            self.write_srt_file()
            
            # Use ffmpeg to embed subtitles in the video
            cmd = [
                'ffmpeg', '-i', self.temp_video, 
                '-vf', f"subtitles={self.temp_srt}:force_style=FontName='LiberationSans-Regular,PrimaryColour=&H0000FF00'", 
                output_path
            ]
            
            try:
                subprocess.run(cmd, check=True)
                print(f"Video with subtitles saved to: {output_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error saving video with subtitles: {e}")
    
    def cleanup(self):
        if self.video_capture:
            self.video_capture.release()
        
        if self.video_writer:
            self.video_writer.release()
        
        cv2.destroyAllWindows()
        
        # Show save dialog if we have recorded anything
        if os.path.exists(self.temp_video):
            self.save_final_video()
            
        # Clean up temporary files
        try:
            os.remove(self.temp_video)
            os.remove(self.temp_srt)
            os.rmdir(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")

if __name__ == "__main__":
    print("Starting Video Subtitler...")
    print("Press 'q' to stop recording and save the video.")
    
    subtitler = VideoSubtitler()
    subtitler.start_recording()

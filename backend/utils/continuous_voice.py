import speech_recognition as sr
import threading
import queue
import logging
from typing import Callable, Optional
import time
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class ContinuousVoiceListener:
    """Continuously listen for voice input and process it automatically."""
    
    def __init__(self, session_id: str, language: str = "en-US"):
        """
        Initialize continuous voice listener.
        
        Args:
            session_id: Session ID for this listener
            language: Language code for speech recognition
        """
        self.session_id = session_id
        self.language = language
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = False
        self.listen_thread = None
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        # Use temp file for communication
        self.voice_file = Path(f"/tmp/voice_input_{session_id}.json")
        
        # Optimize settings for continuous listening
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5
        
    def start(self):
        """Start continuous listening in background thread."""
        if self.is_listening:
            logger.warning("Already listening")
            return
        
        self.is_listening = True
        self.stop_event.clear()
        
        # Start listener thread
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        
        # Start processor thread
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()
        
        logger.info("Continuous voice listening started")
    
    def stop(self):
        """Stop continuous listening."""
        if not self.is_listening:
            return
        
        self.is_listening = False
        self.stop_event.set()
        
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        if self.process_thread:
            self.process_thread.join(timeout=2)
        
        logger.info("Continuous voice listening stopped")
    
    def _listen_loop(self):
        """Background loop that continuously listens for audio."""
        try:
            with sr.Microphone(sample_rate=16000) as source:
                self.microphone = source
                logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info("🎤 Listening continuously... Speak anytime!")
                
                while self.is_listening and not self.stop_event.is_set():
                    try:
                        # Listen for audio
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=15)
                        
                        # Check audio duration
                        audio_duration = len(audio.frame_data) / audio.sample_rate
                        if audio_duration >= 0.5:
                            logger.info(f"Audio captured: {audio_duration:.2f}s - queuing for processing")
                            self.audio_queue.put(audio)
                        else:
                            logger.debug(f"Audio too short ({audio_duration:.2f}s), ignoring")
                            
                    except sr.WaitTimeoutError:
                        # No speech detected in timeout period, continue listening
                        continue
                    except Exception as e:
                        logger.error(f"Error in listen loop: {e}")
                        time.sleep(0.5)
                        
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            self.is_listening = False
    
    def _process_loop(self):
        """Background loop that processes captured audio."""
        while self.is_listening and not self.stop_event.is_set():
            try:
                # Get audio from queue (with timeout to allow checking stop_event)
                try:
                    audio = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Process the audio
                logger.info("Processing speech...")
                try:
                    text = self.recognizer.recognize_google(audio, language=self.language)
                    logger.info(f"✅ Transcribed: {text}")
                    
                    # Write to file for Streamlit to pick up
                    self._write_voice_text(text)
                        
                except sr.UnknownValueError:
                    logger.warning("Could not understand audio")
                except sr.RequestError as e:
                    logger.error(f"API error: {e}")
                except Exception as e:
                    logger.error(f"Processing error: {e}")
                    
            except Exception as e:
                logger.error(f"Error in process loop: {e}")
                time.sleep(0.5)
    
    def _write_voice_text(self, text: str):
        """Write transcribed text to file."""
        try:
            data = {
                "text": text,
                "timestamp": time.time()
            }
            with open(self.voice_file, 'w') as f:
                json.dump(data, f)
            logger.info(f"Voice text written to file: {text}")
        except Exception as e:
            logger.error(f"Error writing voice text: {e}")
    
    def read_voice_text(self) -> Optional[str]:
        """Read and clear transcribed text from file."""
        try:
            if self.voice_file.exists():
                with open(self.voice_file, 'r') as f:
                    data = json.load(f)
                
                # Delete file after reading
                self.voice_file.unlink()
                
                # Check if text is recent (within 5 seconds)
                if time.time() - data.get("timestamp", 0) < 5:
                    return data.get("text")
        except Exception as e:
            logger.debug(f"Error reading voice text: {e}")
        return None
    
    def is_active(self) -> bool:
        """Check if listener is currently active."""
        return self.is_listening
    
    @staticmethod
    def is_microphone_available() -> bool:
        """Check if microphone is available."""
        try:
            with sr.Microphone() as source:
                return True
        except Exception as e:
            logger.error(f"Microphone not available: {str(e)}")
            return False

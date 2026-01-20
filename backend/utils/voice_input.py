import speech_recognition as sr
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class VoiceInputHandler:
    """Handle voice input using speech recognition."""
    
    def __init__(self, language: str = "en-US"):
        """
        Initialize voice input handler.
        
        Args:
            language: Language code for speech recognition (default: en-US)
        """
        self.recognizer = sr.Recognizer()
        self.language = language
        
        # Adjust settings for better recognition
        self.recognizer.energy_threshold = 300  # Lower threshold for quieter speech
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0  # Longer pause before considering speech done
        self.recognizer.phrase_threshold = 0.3  # Minimum seconds of speaking audio
        self.recognizer.non_speaking_duration = 0.5  # Seconds of non-speaking audio to keep
    
    def listen_from_microphone(self, timeout: int = 10, phrase_time_limit: int = 15) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Listen to microphone input and convert to text.
        
        Args:
            timeout: Maximum time to wait for speech to start (seconds)
            phrase_time_limit: Maximum time for a single phrase (seconds)
        
        Returns:
            Tuple of (success, transcribed_text, error_message)
        """
        try:
            with sr.Microphone(sample_rate=16000) as source:
                logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                
                logger.info("Listening... Speak now!")
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                
                logger.info(f"Audio captured. Duration: {len(audio.frame_data) / audio.sample_rate:.2f}s")
                
                # Check if audio is too short
                audio_duration = len(audio.frame_data) / audio.sample_rate
                if audio_duration < 0.5:
                    error_msg = "Audio too short. Please speak for at least 1 second."
                    logger.warning(error_msg)
                    return False, None, error_msg
                
                logger.info("Processing speech with Google API...")
                # Try with show_all to get more details
                try:
                    text = self.recognizer.recognize_google(audio, language=self.language, show_all=False)
                    logger.info(f"Transcribed: {text}")
                    return True, text, None
                except sr.RequestError as e:
                    # If API fails, try offline recognition as fallback
                    error_msg = f"Google API error: {str(e)}. Please check your internet connection."
                    logger.error(error_msg)
                    return False, None, error_msg
                
        except sr.WaitTimeoutError:
            error_msg = "No speech detected. Please try again."
            logger.warning(error_msg)
            return False, None, error_msg
            
        except sr.UnknownValueError:
            error_msg = "Could not understand audio. Please speak clearly."
            logger.warning(error_msg)
            return False, None, error_msg
            
        except sr.RequestError as e:
            error_msg = f"Network error: {str(e)}. Check internet connection."
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def transcribe_audio_data(self, audio_data: sr.AudioData) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Audio data from speech_recognition
        
        Returns:
            Tuple of (success, transcribed_text, error_message)
        """
        try:
            text = self.recognizer.recognize_google(audio_data, language=self.language)
            logger.info(f"Transcribed: {text}")
            return True, text, None
            
        except sr.UnknownValueError:
            error_msg = "Could not understand audio"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except sr.RequestError as e:
            error_msg = f"Speech recognition service error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def set_language(self, language: str):
        """
        Set the language for speech recognition.
        
        Args:
            language: Language code (e.g., 'en-US', 'es-ES', 'fr-FR')
        """
        self.language = language
        logger.info(f"Language set to: {language}")
    
    @staticmethod
    def get_supported_languages() -> dict:
        """
        Get dictionary of supported languages.
        
        Returns:
            Dictionary mapping language names to codes
        """
        return {
            "English (US)": "en-US",
            "English (UK)": "en-GB",
            "Spanish": "es-ES",
            "French": "fr-FR",
            "German": "de-DE",
            "Italian": "it-IT",
            "Portuguese": "pt-PT",
            "Russian": "ru-RU",
            "Japanese": "ja-JP",
            "Chinese (Mandarin)": "zh-CN",
            "Korean": "ko-KR",
            "Arabic": "ar-SA",
            "Hindi": "hi-IN"
        }
    
    @staticmethod
    def is_microphone_available() -> bool:
        """
        Check if microphone is available.
        
        Returns:
            True if microphone is available, False otherwise
        """
        try:
            with sr.Microphone() as source:
                return True
        except Exception as e:
            logger.error(f"Microphone not available: {str(e)}")
            return False

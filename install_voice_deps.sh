#!/bin/bash

# Installation script for voice input dependencies

echo "🎤 Installing Voice Input Dependencies..."
echo ""

# Check OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Detected macOS"
    echo "Installing portaudio (required for PyAudio)..."
    brew install portaudio
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Detected Linux"
    echo "Installing portaudio and python3-pyaudio..."
    sudo apt-get update
    sudo apt-get install -y portaudio19-dev python3-pyaudio
else
    echo "⚠️  Unknown OS. Please install portaudio manually."
fi

echo ""
echo "📦 Installing Python packages..."
pip install SpeechRecognition>=3.10.0
pip install pydub>=0.25.1
pip install pyaudio>=0.2.14

echo ""
echo "✅ Voice input dependencies installed!"
echo ""
echo "🎤 To test microphone access, run:"
echo "   python -c 'import speech_recognition as sr; print(sr.Microphone.list_microphone_names())'"

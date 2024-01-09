# Transcriptor Project

## Overview

Transcriptor is an advanced transcription tool that leverages the OpenAI Whisper Tiny model to convert speech from audio files, YouTube videos, or live input into text. It features a user-friendly frontend built with Streamlit and a robust backend designed with FastAPI and WebSockets, providing real-time transcription capabilities with high accuracy.

## Features

- Transcribe audio from local files (.wav format).
- Transcribe content directly from YouTube URLs.
- Real-time transcription through live audio input.
- Simple and intuitive user interface.
- Option to download transcriptions as a text file.

## How It Works

1. **Select a Mode of Operation**: Choose whether to upload an audio file, enter a YouTube URL, or start live transcription.
2. **Upload or Input**: Depending on the selected mode, either upload an audio file, enter a YouTube URL, or begin speaking when prompted.
3. **Review**: Wait for the transcription to complete and then review your transcribed text.
4. **Download**: Get a copy of the transcribed text by downloading it directly from the interface.

## Installation

To set up the Transcriptor project locally, you need to have Docker and Docker Compose installed on your machine.

1. Clone the repository (ssh example):
   ```sh
   git clone git@github.com:firefly-cmd/VerbalizeIt.git

2. Navigate to the project directory:
   ```sh
   cd VerbalizeIt
3. Use Docker Compose to build and run the containers:
   ```sh
   docker-compose up --build
## Usage
The frontend at: http://localhost:8501
The backend at: http://localhost:8000
   

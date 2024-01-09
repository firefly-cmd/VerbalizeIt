from uuid import uuid4
import os
import tempfile
from io import BytesIO
from typing import Dict

from fastapi import FastAPI, BackgroundTasks, UploadFile, File, WebSocket
from pydantic import BaseModel
import numpy as np
import whisper
from pytube import YouTube
from pydub import AudioSegment

# Initialize the app
app = FastAPI()


# Schema for youtube transcription api
class YoutubeUrl(BaseModel):
    youtube_url: str


# In-memory storage for task status
tasks = {}

# Load the Whisper model
model = whisper.load_model("tiny.en")


def create_task_id() -> str:
    """
    Generates a unique task identifier using UUID4.

    This function creates a universally unique identifier (UUID)
    which can be used as a task ID for tracking individual transcription tasks.

    Returns:
        str: A unique task identifier as a string.
    """
    # Generate and return a new UUID4
    return str(uuid4())


async def process_local_audio_file(task_id: str, upload_file: UploadFile) -> None:
    """
    Processes an uploaded audio file for transcription using the Whisper model.

    This function reads an audio file from an UploadFile object, processes it,
    and transcribes it using the globally loaded Whisper model. The result of the
    transcription is stored in the global 'tasks' dictionary.

    Args:
        task_id (str): A unique identifier for the transcription task.
        upload_file (UploadFile): The audio file uploaded by the user.

    Raises:
        Exception: If an error occurs during file processing or transcription.
    """
    try:
        # Extract the audio bytes from the uploaded file
        audio_bytes = await upload_file.read()

        # Use pydub to handle different audio formats and convert audio
        audio = AudioSegment.from_file(BytesIO(audio_bytes))
        audio = audio.set_channels(1).set_frame_rate(16000)

        # Convert the audio to a raw data byte string
        raw_data = audio.raw_data

        # Convert the raw data into a NumPy array for processing
        audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
        audio_np /= np.iinfo(np.int16).max  # Normalize to range [-1.0, 1.0]

        # Transcribe the audio using the Whisper model
        result = model.transcribe(audio_np)
        transcription = result.get("text")

        # Update the task status with the transcription result
        tasks[task_id] = {"status": "completed", "transcription": transcription}
    except Exception as e:
        # Handle any errors that occur during the processing
        tasks[task_id] = {"status": "failed", "error": str(e)}


def download_youtube_audio(youtube_url: str) -> str:
    """
    Downloads the audio stream of a YouTube video to a temporary file.

    Given a YouTube URL, this function downloads the audio stream with the highest bitrate
    available and saves it to a temporary file. The path to the saved audio file is then returned.

    Args:
        youtube_url (str): The URL of the YouTube video from which to download the audio.

    Returns:
        str: The file path to the downloaded audio file.

    Raises:
        PytubeError: If an error occurs in downloading the audio from YouTube.
    """
    try:
        # Initialize a YouTube object with the given URL
        yt = YouTube(youtube_url)

        # Select the highest bitrate audio stream available
        audio_stream = (
            yt.streams.filter(only_audio=True).order_by("bitrate").desc().first()
        )

        # Generate a temporary file path for storing the downloaded audio
        temp_dir = tempfile.gettempdir()
        temp_filename = audio_stream.default_filename
        temp_filepath = os.path.join(temp_dir, temp_filename)

        # Download the audio stream to the temporary file
        audio_stream.download(output_path=temp_dir, filename=temp_filename)

        return temp_filepath
    except Exception as e:
        # TODO Consider specific exception handling related to Pytube or network issues
        raise Exception(f"Error downloading YouTube audio: {e}")


def process_youtube_audio(task_id: str, file_path: str) -> None:
    """
    Processes and transcribes a YouTube audio file using the Whisper model.

    This function reads an audio file from the given file path, transcribes it using
    the globally loaded Whisper model, and updates the task status in the global
    'tasks' dictionary. It handles any errors during transcription and ensures
    that the temporary audio file is removed after processing.

    Args:
        task_id (str): The unique identifier of the transcription task.
        file_path (str): The file path of the audio file to be transcribed.

    Raises:
        Exception: If an error occurs during transcription.
    """
    try:
        # Transcribe the audio file using the Whisper model
        result = model.transcribe(file_path)
        transcription = result.get("text")

        # Update the task status with the transcription result
        tasks[task_id] = {"status": "completed", "transcription": transcription}
    except Exception as e:
        # Handle any errors that occur during transcription
        tasks[task_id] = {"status": "failed", "error": str(e)}
    finally:
        # Ensure the temporary file is removed after processing
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/status/{task_id}")
async def check_status(task_id: str) -> Dict[str, str]:
    """
    Endpoint to check the status of a transcription task.

    Given a task ID, this endpoint returns the current status of the transcription task.
    It could be 'processing', 'completed', or 'failed'. If the task ID is not found,
    it returns a status indicating that the task is not found.

    Args:
        task_id (str): The unique identifier of the transcription task.

    Returns:
        Dict[str, str]: A dictionary containing the status of the task. If the task is
        completed, it also includes the transcription text.
    """
    # Retrieve the task by its ID
    task = tasks.get(task_id)

    # Check if the task exists and return its status
    if task:
        return task

    return {"status": "not found"}


@app.post("/transcribe-local/")
async def transcribe_local_file(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
) -> Dict[str, str]:
    """
    Endpoint to handle the transcription of a locally uploaded audio file.

    This endpoint receives an audio file uploaded by the user, creates a task ID,
    and enqueues a background task to process and transcribe the audio file.
    It returns the task ID for status tracking.

    Args:
        background_tasks (BackgroundTasks): FastAPI utility for background task execution.
        file (UploadFile, optional): The audio file uploaded by the user.

    Returns:
        Dict[str, str]: A dictionary containing the task ID.
    """
    # Generate a unique task ID for this transcription request
    task_id = create_task_id()

    # Set the initial status of the task
    tasks[task_id] = {"status": "processing"}

    # Enqueue the audio processing and transcription task
    background_tasks.add_task(process_local_audio_file, task_id, file)

    # Return the task ID for status tracking
    return {"task_id": task_id}


@app.post("/transcribe-youtube/")
async def transcribe_youtube(
    background_tasks: BackgroundTasks, youtube_url: YoutubeUrl
) -> Dict[str, str]:
    """
    Endpoint to handle the transcription of a YouTube video.

    This endpoint receives a YouTube URL, creates a task ID for tracking,
    and enqueues a background task to download the video's audio and
    transcribe it. The task ID is returned for the client to track the
    status of the transcription process.

    Args:
        background_tasks (BackgroundTasks): FastAPI utility for background task execution.
        youtube_url (YoutubeUrl): Pydantic model that contains the YouTube video URL.

    Returns:
        Dict[str, str]: A dictionary containing the task ID for the transcription job.
    """
    # Generate a unique task ID for this transcription request
    task_id = create_task_id()

    # Set the initial status of the task
    tasks[task_id] = {"status": "processing"}

    # Enqueue the task for downloading and transcribing the YouTube audio
    background_tasks.add_task(
        process_youtube_audio, task_id, download_youtube_audio(youtube_url.youtube_url)
    )

    # Return the task ID for status tracking
    return {"task_id": task_id}


@app.websocket("/ws")
async def transcribe_websocket_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time audio transcription.

    This endpoint handles a WebSocket connection for real-time audio data streaming.
    It receives audio data from the client, transcribes it using the Whisper model,
    and sends the transcription text back to the client through the WebSocket.

    Args:
        websocket (WebSocket): The WebSocket connection with the client.

    Raises:
        Exception: If an error occurs during the WebSocket communication or transcription process.
    """
    await websocket.accept()
    try:
        while True:
            # Receive audio data from the client
            data = await websocket.receive_bytes()

            # Convert the received data to a NumPy array and process it
            updated_data = np.frombuffer(data, dtype=np.float32).copy()
            transcription = model.transcribe(updated_data)

            # Send the transcription result back to the client
            await websocket.send_text(transcription["text"])
    except Exception as e:
        # Log any exceptions that occur
        print(f"Error in WebSocket communication: {e}")
    finally:
        # Close the WebSocket connection when done
        await websocket.close()

import time
from typing import Optional

import requests
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from transformers.pipelines.audio_utils import ffmpeg_microphone_live
from websockets.sync.client import connect


def handle_local_file_transcription(
    uploaded_file: UploadedFile,
    fastapi_endpoint: str,
    status_endpoint: str,
) -> Optional[str]:
    """
    Handles the transcription of a locally uploaded file by sending it to a FastAPI backend,
    polling for the transcription results, and displaying them in the Streamlit app.

    Args:
        uploaded_file (UploadedFile): The uploaded file object from Streamlit.
        fastapi_endpoint (str): The endpoint URL for the FastAPI transcription service.
        status_endpoint (str): The endpoint URL to check the status of the transcription task.

    Returns:
        Optional[str]: The task ID if the transcription is started successfully, otherwise None.
    """

    try:
        files = {"file": uploaded_file.getvalue()}
        response = requests.post(fastapi_endpoint, files=files)

        if response.status_code == 200:
            task_id = response.json().get("task_id")
            st.write("Processing... Please wait.")

            # Continuously poll for results
            while True:
                response = requests.get(f"{status_endpoint}/{task_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "completed":
                        transcription = result.get("transcription")
                        st.text_area(
                            "Transcribed text", value=transcription, height=500
                        )

                        # Option to download the transcription
                        st.download_button(
                            label="Download Transcription",
                            data=transcription,
                            file_name="transcription.txt",
                            mime="text/plain",
                        )
                        break  # Exit loop if transcription is completed
                    elif result.get("status") == "failed":
                        st.error("Transcription failed.")
                        break  # Exit loop if transcription fails
                time.sleep(0.5)  # Delay between polling requests
        else:
            st.error("Failed to start transcription process.")
            return None

        return task_id

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None


def handle_youtube_transcription(
    youtube_url: str, fastapi_endpoint_youtube: str, status_endpoint: str
) -> Optional[str]:
    """
    Handles the transcription of a YouTube video by sending its URL to a FastAPI backend,
    polling for the transcription results, and displaying them in the Streamlit app.

    Args:
        youtube_url (str): The URL of the YouTube video to be transcribed.
        fastapi_endpoint_youtube (str): The endpoint URL for the FastAPI YouTube transcription service.
        status_endpoint (str): The endpoint URL to check the status of the transcription task.

    Returns:
        Optional[str]: The task ID if the transcription is started successfully, otherwise None.
    """

    try:
        # Send the YouTube URL to the FastAPI backend
        response = requests.post(
            fastapi_endpoint_youtube, json={"youtube_url": youtube_url}
        )

        if response.status_code == 200:
            task_id = response.json().get("task_id")
            st.info(
                "Processing... Please wait. This may take some time for long youtube videos"
            )

            # Continuously poll for results
            while True:
                response = requests.get(f"{status_endpoint}/{task_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "completed":
                        transcription = result.get("transcription")
                        st.text_area(
                            "Transcribed text", value=transcription, height=500
                        )

                        # Option to download the transcription
                        st.download_button(
                            label="Download Transcription",
                            data=transcription,
                            file_name="transcription.txt",
                            mime="text/plain",
                        )
                        break  # Exit loop if transcription is completed
                    elif result.get("status") == "failed":
                        st.error("Transcription failed.")
                        break  # Exit loop if transcription fails
                time.sleep(0.5)  # Delay between polling requests
        else:
            st.error("Failed to start transcription process.")
            return None

        return task_id

    except Exception as e:
        # Handle any exceptions that occur during the process
        st.error(f"An error occurred: {e}")
        return None


def handle_live_transcription(sampling_rate: int, websocket_url: str) -> None:
    """
    Establishes a WebSocket connection to receive live transcription of audio captured
    from the microphone. The transcription is displayed in real-time in the Streamlit app.

    Args:
        sampling_rate (int): The sampling rate for the microphone input.
        websocket_url (str): The URL of the WebSocket server to send audio data for transcription.

    Returns:
        None: This function does not return anything but updates the Streamlit app directly.
    """

    # Open the WebSocket connection
    with connect(websocket_url) as websocket:
        # Start the microphone input stream
        chunk_length_s = 5
        stream_chunk_s = 1
        mic = ffmpeg_microphone_live(
            sampling_rate=sampling_rate,
            chunk_length_s=chunk_length_s,
            stream_chunk_s=stream_chunk_s,
        )

        st.info("You can start talking")

        # Initialize transcription display and stop recording button in the Streamlit app
        transcription_display = st.empty()
        stop_recording = st.empty()

        # Check and display existing transcription if present in the session state
        if "live_transcription" in st.session_state:
            transcription_display.text_area(
                "Transcription",
                value=st.session_state["live_transcription"],
                height=300,
            )

        live_recording_key = 0

        # Process audio chunks from the microphone input
        for item in mic:
            if not st.session_state.get("stop_recording", False):
                if not item["partial"]:
                    # Send the audio data to the WebSocket server
                    websocket.send(item["raw"].tobytes())
                    message = websocket.recv()

                    # Update the transcription in the session state
                    st.session_state["live_transcription"] = (
                        st.session_state.get("live_transcription", "") + message
                    )

                    # Display the updated transcription
                    transcription_display.text_area(
                        "Transcription",
                        value=st.session_state["live_transcription"],
                        height=300,
                        key=f"Transcription_{live_recording_key}",
                    )

                    # Button to stop recording
                    st.session_state["stop_recording"] = stop_recording.button(
                        "Stop Recording",
                        key=f"StopRecording_{live_recording_key}",
                    )

                    live_recording_key += 1
            else:
                break  # Exit loop if stop recording is requested

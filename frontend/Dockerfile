# Use an official Python 3.10 runtime as a base image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy the frontend requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages 
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the frontend application
COPY ./ /app

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Run app.py when the container launches
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

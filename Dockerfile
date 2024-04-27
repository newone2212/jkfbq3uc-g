# Use an official Ubuntu base image
FROM ubuntu:20.04

# Set environment variables to avoid user interaction during installations
ENV DEBIAN_FRONTEND=noninteractive

# Update the system
RUN apt-get update && apt-get upgrade -y

# Install Python and other necessary system dependencies
RUN apt-get install -y \
    software-properties-common \
    python3.8 \
    python3-pip \
    wget \
    sudo \
    xvfb \
    xserver-xephyr \
    tigervnc-standalone-server \
    xfonts-base \
    pulseaudio-utils \
    lame \
    mpg123 \
    libasound2 \
    libasound2-plugins \
    alsa-utils \
    alsa-oss \
    pulseaudio \
    libappindicator1 \
    fonts-liberation \
    git

# Install Google Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

# Clone the repository and setup the working directory
RUN git clone https://github.com/atharva-lipare/acta-demo.git /app
WORKDIR /app
RUN mkdir recordings

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Install additional Python dependencies
RUN pip3 install uvicorn[standard]

# Setup pulseaudio daemon
RUN usermod -aG pulse,pulse-access root
COPY pulseaudio-daemon.conf /etc/pulse/daemon.conf
RUN pulseaudio -D

# Expose port 8000 for the application
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

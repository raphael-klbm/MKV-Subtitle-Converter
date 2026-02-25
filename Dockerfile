FROM debian:12

RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    gnupg

RUN mkdir -p /etc/apt/keyrings && \
    wget -O /etc/apt/keyrings/gpg-pub-moritzbunkus.gpg https://mkvtoolnix.download/gpg-pub-moritzbunkus.gpg

RUN echo "deb [signed-by=/etc/apt/keyrings/gpg-pub-moritzbunkus.gpg] https://mkvtoolnix.download/debian/ bookworm main" \
    > /etc/apt/sources.list.d/mkvtoolnix.download.list

RUN apt update && \
    apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-tk \
    tesseract-ocr-all \
    ffmpeg \
    mkvtoolnix \
    libx11-6 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY main.py .
COPY config.py .
COPY backend backend
COPY controller controller
COPY gui gui
COPY languages languages
COPY licenses licenses
COPY requirements.txt requirements.txt

# Create a virtual environment and activate it
RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Install Python dependencies
RUN python3 -m pip install -r requirements.txt

CMD ["python3", "main.py"]
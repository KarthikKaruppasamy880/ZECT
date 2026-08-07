FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ml.txt ./
# CPU torch first, then chatterbox (requirements-ml has no torch pin).
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements-ml.txt

COPY app ./app

ENV ZECT_VOICEBOX_PORT=17493
ENV ZECT_VOICEBOX_BACKEND=native
ENV ZECT_VOICEBOX_DATA_DIR=/data
ENV ZECT_VOICEBOX_MODEL_DIR=/models
ENV ZECT_VOICEBOX_SYNTH=chatterbox
ENV ZECT_VOICEBOX_ALLOW_STUB=0
ENV HF_HOME=/models/huggingface

EXPOSE 17493
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "17493"]

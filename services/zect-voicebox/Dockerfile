FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

ENV ZECT_VOICEBOX_PORT=17493
ENV ZECT_VOICEBOX_BACKEND=native
ENV ZECT_VOICEBOX_DATA_DIR=/data
ENV ZECT_VOICEBOX_MODEL_DIR=/models
ENV ZECT_VOICEBOX_SYNTH=auto
ENV ZECT_VOICEBOX_ALLOW_STUB=1

EXPOSE 17493
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "17493"]

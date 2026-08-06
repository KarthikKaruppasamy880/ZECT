FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

ENV ZECT_VOICEBOX_PORT=17493
ENV ZECT_VOICEBOX_BACKEND=upstream
ENV ZECT_VOICEBOX_DATA_DIR=/data

EXPOSE 17493
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "17493"]

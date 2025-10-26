FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd -m -d /home/myuser myuser

RUN mkdir -p /resources/audios && \
    mkdir -p /resources/videos && \
    mkdir -p /resources/subtitles && \
    chown -R myuser:myuser /resources && \
    chmod 755 -R /resources

USER myuser

RUN python -m venv /home/myuser/venv
ENV PATH="/home/myuser/venv/bin:$PATH"

RUN pip install --upgrade pip

WORKDIR /app
RUN 

COPY --chown=myuser:myuser ./app /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD  ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]

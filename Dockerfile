FROM python:3.10-slim

WORKDIR /app

# install only required libs
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

RUN pip install --upgrade pip

# 🔥 VERY IMPORTANT FLAGS
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

CMD ["python", "bot.py"]

FROM python:3.10-slim

# Install system deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy files
COPY . .

# Install python deps
RUN pip install --no-cache-dir -r requirements.txt

# Create folders
RUN mkdir -p downloads frames

# Run bot
CMD ["python", "bot.py"]

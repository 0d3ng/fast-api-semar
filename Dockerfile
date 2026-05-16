# Menggunakan base image Python versi 3.12.5
FROM python:3.12.5

# Install dependencies + timezone JST
RUN apt-get update && apt-get install -y wget unzip iputils-ping tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && wget -O /tmp/chromium.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chromium.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/chromium.deb

# Set working directory
WORKDIR /app

# Copy file requirements.txt ke working directory
COPY requirements.txt .

# Menginstall dependencies dari requirements.txt
RUN pip install --progress-bar off --upgrade pip
RUN pip install --progress-bar off --no-cache-dir -r requirements.txt

# Copy seluruh file di direktori lokal ke working directory di container
COPY . .

# Menjalankan aplikasi
CMD ["sh", "-c", "uvicorn app.main:app --workers 1 --host 0.0.0.0 --port 8001"]
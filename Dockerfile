# Menggunakan base image Python versi 3.8.10
FROM python:3.12.5

# Set working directory
WORKDIR /app

# Copy file requirements.txt ke working directory
COPY requirements.txt .

# Menginstall dependencies dari requirements.txt
RUN pip install --progress-bar off --upgrade pip
RUN pip install --progress-bar off --no-cache-dir -r requirements.txt

# Copy seluruh file di direktori lokal ke working directory di container
COPY . .

# Menetapkan perintah default untuk menjalankan aplikasi
# Environment variable ENV bisa diatur melalui perintah `docker run`
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 9092"]

# FAST API SEMAR SERVER
Implement IoT Platform system using FastAPI

## How to run
To run the application using `uvicorn`
### Install dependency first
Please type command `pip install -r requirements.txt`

### Running application
Using command uvicorn `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### Running inside single container 
`docker run --network host --name fast-api-semar --env-file .env -v logs:/app/logs -p 8001:8001 0d3ng/fast-api-semar:v1`

### Generate Key Secret Token
The python file in `ecc_tools.py`, type `export PYTHONPATH=$(pwd)` first

### Build image
`docker build -t fast-api-semar:ota .`

### Build image and push to docker hub
`docker build -t 0d3ng/fast-api-semar:ota --push .`
# FAST API SEMAR SERVER
Implement IoT Platform system using FastAPI

## How to run
To run the application using `uvicorn`
### Install dependency first
Please type command `pip install -r requirements.txt`

### Running application
Using command uvicorn `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### Generate Key Secret Token
The python file in `ecc_tools.py`, type `export PYTHONPATH=$(pwd)` first
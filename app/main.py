import signal

import fastapi
from fastapi import FastAPI
from app.routes import user_routes
import uvicorn
import os
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI()


def shutdown():
    os.kill(os.getpid(), signal.SIGTERM)
    return fastapi.Response(status_code=200, content='Server shutting down...')


@app.on_event('shutdown')
def on_shutdown():
    logger.info('Server shutting down...')


app.include_router(user_routes.router, prefix="/api", tags=["Users"])
app.add_api_route('/shutdown', shutdown, methods=['GET'])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

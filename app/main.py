from fastapi import FastAPI
from app.routes import user_routes
import uvicorn

app = FastAPI()

app.include_router(user_routes.router, prefix="/api", tags=["Users"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

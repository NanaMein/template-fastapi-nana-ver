from fastapi import FastAPI

from src.core.lifespan import lifespan
from src.routers.auth import auth_router

app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

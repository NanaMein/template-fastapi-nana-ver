from fastapi import FastAPI, HTTPException
from loguru import logger

from src.core.lifespan import lifespan
from src.core.logger import initialize_setup_logger
from src.routers.auth import auth_router

initialize_setup_logger()

app = FastAPI(lifespan=lifespan, title="FastAPI Template")
app.include_router(auth_router)

_counter = 0
@app.get("/")
async def root():
    global _counter
    _counter += 1
    if _counter % 2 == 0:
        logger.info(f"Counter: {_counter}, success")
        return {"message": "Hello World"}

    logger.error(f"Counter: {_counter}, failure")
    raise HTTPException(status_code=400, detail="Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

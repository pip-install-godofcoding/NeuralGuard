import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import completions, health, keys
from services.cache import init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield


app = FastAPI(
    title="NeuralGuard",
    description="Transparent LLM proxy with semantic caching and trust scoring",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(completions.router, prefix="/v1")
app.include_router(keys.router, prefix="/admin")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)

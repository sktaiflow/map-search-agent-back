from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.container import Container
from app.api.agents import router as agents_router
from configs import config
from utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    container = Container()
    container.wire(packages=["app"])
    app.container = container
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=config.app_name,
        version=config.api_version,
        description="Map Search Agent Backend API",
        lifespan=lifespan,
    )
    
    # Include routers
    app.include_router(agents_router, prefix="/api")
    
    return app


app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": config.api_version}
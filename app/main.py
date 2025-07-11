from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine, Base
from app.api.v1 import auth, users, tasks, analytics, ai
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request


# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics & Dashboard"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI Assistant"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to TaskMaster API with Advanced Analytics! 📊",
        "version": settings.VERSION,
        "features": [
            "Task Management",
            "User Authentication", 
            "Completion Trends Analysis",
            "Performance Dashboard",
            "Productivity Insights"
        ],
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

@app.exception_handler(HTTPException)
async def llama_http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/v1/ai") and exc.status_code == 503:
        return JSONResponse(
            status_code=503,
            content={
                "error": "LLaMA Service Unavailable",
                "message": "Please ensure Ollama is running and the model is downloaded",
                "troubleshooting": {
                    "check_ollama": "Run 'ollama list' to see available models",
                    "start_ollama": "Start Ollama service if not running",
                    "download_model": "Run 'ollama pull llama2' to download the model"
                }
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )
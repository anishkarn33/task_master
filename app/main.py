from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine, Base
from app.api.v1 import auth, users, tasks, analytics

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
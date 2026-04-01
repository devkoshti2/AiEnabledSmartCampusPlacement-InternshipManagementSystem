from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.routers import auth, students, admin, upload, resume_processor, matching, ai_predictions, notifications, export, otp, ranking
from app.database import create_tables
from app.routers import selection_v2
from app.routers import matching_v2
from app.routers import eligibility_v2
from app.routers import skill_gap_v2
from app.routers import skill_analysis
from app.routers import ranking
import asyncio
from app.utils.email_sender import process_email_queue
import logging
import nltk
import os
from pathlib import Path

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables on startup
create_tables()

app = FastAPI(title="AI Placement System", version="1.0.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (uploads)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ✅ IMPORTANT: Serve frontend files
# Get the absolute path to the frontend folder
current_dir = Path(__file__).parent.parent  # This goes to backend folder
frontend_path = current_dir.parent / "frontend"  # This goes to root/frontend

# Ensure frontend path exists
if frontend_path.exists():
    logger.info(f"✅ Frontend folder found at: {frontend_path}")
    app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")
else:
    logger.warning(f"❌ Frontend folder NOT found at: {frontend_path}")
    # Try alternative path (if running from root)
    alt_frontend_path = Path.cwd() / "frontend"
    if alt_frontend_path.exists():
        logger.info(f"✅ Frontend folder found at alternative path: {alt_frontend_path}")
        app.mount("/frontend", StaticFiles(directory=str(alt_frontend_path)), name="frontend")
        frontend_path = alt_frontend_path

# Include all routers
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(admin.router)
app.include_router(upload.router)
app.include_router(resume_processor.router)
app.include_router(matching.router)
app.include_router(ai_predictions.router)
app.include_router(notifications.router)
app.include_router(export.router)
app.include_router(otp.router)
app.include_router(skill_analysis.router)
app.include_router(eligibility_v2.router)
app.include_router(selection_v2.router)
app.include_router(matching_v2.router)
app.include_router(skill_gap_v2.router)
app.include_router(ranking.router)

try:
    from app.routers import ranking
    app.include_router(ranking.router)
    logger.info("✅ Ranking router included")
except ImportError:
    logger.warning("⚠️ Ranking router not found - skipping")

@app.get("/", include_in_schema=False)
async def serve_root():
    """Serve index.html for root path"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"error": "Frontend files not found"}, status_code=404)

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

async def email_queue_processor():
    """Har 30 second mein email queue process karo"""
    while True:
        try:
            logger.info("Processing email queue...")
            process_email_queue()
            logger.info("Email queue processed")
        except Exception as e:
            logger.error(f"Email queue processor error: {e}")
        
        # 1 second wait karo (instead of 2 minutes)
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up... Checking AI models")

    # Start email queue processor
    if not hasattr(app, "email_processor_task"):
        app.email_processor_task = asyncio.create_task(email_queue_processor())
        logger.info("✅ Email queue processor started")

    try:
        from app.ai.models import EligibilityPredictor, SelectionProbabilityPredictor
        # Initialize models (they'll auto-train if needed)
        eligibility_predictor = EligibilityPredictor()
        selection_predictor = SelectionProbabilityPredictor()
        logger.info("✅ AI models initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize AI models: {e}")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """Serve all frontend files (HTML, CSS, JS, etc.)"""
    
    # ✅ IMPORTANT: API routes ko allow karo - 404 mat do
    # Agar path API route se start ho raha hai, toh 404 return karo (API router handle karega)
    api_prefixes = ['auth/', 'admin/', 'student/', 'upload/', 'resume/', 'matching/', 'ai/', 'notifications/', 'export/', 'static/', 'otp/']
    
    for prefix in api_prefixes:
        if full_path.startswith(prefix):
            # API routes ke liye 404 return karo - actual router handle karega
            return JSONResponse({"error": f"API endpoint - use /{prefix}"}, status_code=404)
    
    # Check if file has extension (like .html, .css, .js)
    if '.' in full_path:
        file_path = frontend_path / full_path
        if file_path.exists():
            return FileResponse(str(file_path))
    
    # Check for HTML file without extension (e.g., "login" -> "login.html")
    html_file = frontend_path / f"{full_path}.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    
    # Check for admin pages
    if full_path.startswith("admin/"):
        admin_file = frontend_path / full_path
        if admin_file.exists():
            return FileResponse(str(admin_file))
        
        admin_html = frontend_path / f"{full_path}.html"
        if admin_html.exists():
            return FileResponse(str(admin_html))
    
    # Check if it's a file in root directory
    root_file = frontend_path / full_path
    if root_file.exists() and root_file.is_file():
        return FileResponse(str(root_file))
    
    # If nothing found, try index.html (for client-side routing)
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    
    return JSONResponse({"error": f"File not found: {full_path}"}, status_code=404)
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import threading
from core.logger import logger
from core.config import settings

# Importar routers
from web.routers import auth, pacientes, medicos, recetas, local_admin

# Startup/Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 RecetasWebApp iniciando...")
    
    #try:
        #from jobs.receiver_job import job_receiver
        #thread = threading.Thread(target=job_receiver, daemon=True)
        #thread.start()
        #logger.info("✅ Job receiver iniciado")
    #except Exception as e:
        #logger.warning(f"⚠️ Error iniciando job receiver: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 RecetasWebApp apagándose...")

# Crear app
app = FastAPI(
    title="Recetario Médico API",
    description="Sistema integral de gestión de recetas médicas",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
logger.info("Registrando routers...")

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(pacientes.router, prefix="/api", tags=["pacientes"])
app.include_router(medicos.router, prefix="/api", tags=["medicos"])
app.include_router(recetas.router, prefix="/api", tags=["recetas"])
app.include_router(local_admin.router, prefix="/api", tags=["local_admin"])

logger.info("✅ Routers registrados")

# Health check
@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

"""
Minimal FastAPI app. Fill in real data access against
src/storage/snapshot.py once the pipeline is producing profiles.

Run: uvicorn src.api.main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from src.storage.snapshot import latest_snapshot
from src.config import settings

app = FastAPI(title="Signalpost Norway Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production if necessary
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/companies")
def list_companies() -> dict:
    snapshots_dir = Path(settings.data_dir) / "snapshots"
    if not snapshots_dir.exists():
        return {"companies": []}
    
    companies = []
    # Folders are org_numbers
    for org_dir in snapshots_dir.iterdir():
        if org_dir.is_dir():
            latest = latest_snapshot(org_dir.name)
            if latest:
                companies.append({
                    "org_number": latest.entity.org_number,
                    "legal_name": latest.entity.legal_name,
                    "status": latest.entity.status,
                    "last_updated": latest.profile_generated_at
                })
    return {"companies": companies}


@app.get("/companies/{org_number}")
def get_company(org_number: str) -> dict:
    profile = latest_snapshot(org_number)
    if profile is None:
        raise HTTPException(status_code=404, detail="No snapshot found for this org number")
    return profile.model_dump()

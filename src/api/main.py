"""
Minimal FastAPI app. Fill in real data access against
src/storage/snapshot.py once the pipeline is producing profiles.

Run: uvicorn src.api.main:app --reload
"""

from fastapi import FastAPI, HTTPException

from src.storage.snapshot import latest_snapshot

app = FastAPI(title="Signalpost Norway Agent API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/companies/{org_number}")
def get_company(org_number: str) -> dict:
    profile = latest_snapshot(org_number)
    if profile is None:
        raise HTTPException(status_code=404, detail="No snapshot found for this org number")
    return profile.model_dump()

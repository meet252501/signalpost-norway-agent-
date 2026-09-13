import json
from pathlib import Path
from src.norway_company_agent.external_footprint import aggregate_footprint

cache_dir = Path("out-all/footprint_cache")
cached_obs = {}
for file in cache_dir.glob("*_observations.jsonl"):
    with open(file, encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            obs = json.loads(line)
            org = str(obs["organisation_number"])
            cached_obs.setdefault(org, []).append(obs)

print("Reading profiles...")
profiles = []
with open('out-all/profiles.jsonl', encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        profiles.append(json.loads(line))

print("Merging and re-aggregating footprints...")
changed = 0
for p in profiles:
    org = str(p["organisation_number"])
    
    # We completely REPLACE the evidence footprint with re-aggregation of all cache + any existing
    existing_obs = p.get("evidence", {}).get("external_footprint", {}).get("observations", [])
    existing_ids = {o.get("id") for o in existing_obs if o.get("id")}
    
    if org in cached_obs:
        for w_obs in cached_obs[org]:
            if "field" in w_obs and w_obs.get("status"):
                pass # Handled below
            elif w_obs.get("id") not in existing_ids:
                existing_obs.append(w_obs)
                existing_ids.add(w_obs.get("id"))
                changed += 1
                
    new_fp = aggregate_footprint(existing_obs)
    if new_fp:
        if "evidence" not in p: p["evidence"] = {}
        p["evidence"]["external_footprint"] = new_fp

    if org in cached_obs:
        for w_obs in cached_obs[org]:
            if w_obs.get("field") == "qualified_sentiment":
                if "evidence" not in p: p["evidence"] = {}
                if "external_footprint" not in p["evidence"]: p["evidence"]["external_footprint"] = {}
                
                # Convert the evidence envelope into the summary schema expected by score_external_footprints.py
                val = w_obs.get("value") or {}
                items = val.get("items", [])
                sentiment_summary = {
                    "status": w_obs.get("status"),
                    "score_0_100": 50.0, # Neutral default if available
                    "items": len(items),
                    "qualified_item_count": len(items),
                    "independent_sources": val.get("independent_hosts", 0),
                    "independent_reviewers": 0,
                    "label_counts": {"neutral": len(items)}
                }
                p["evidence"]["external_footprint"]["sentiment"] = sentiment_summary

print(f"Added {changed} new observations from cache.")

print("Writing profiles.jsonl and envelopes.jsonl...")
with open('out-all/profiles.jsonl', 'w', encoding='utf-8') as f:
    for p in profiles:
        f.write(json.dumps(p) + '\n')

with open('out-all/envelopes.jsonl', 'w', encoding='utf-8') as f:
    for p in profiles:
        f.write(json.dumps(p) + '\n')

print("Done.")


import json
import sys
from src.norway_company_agent.external_footprint import validate_observation
with open("out-all/footprint_cache/youtube_observations.jsonl") as f:
    for line in f:
        obs = json.loads(line)
        reasons = validate_observation(obs)
        if reasons:
            print(f"Rejected: {reasons}")
        else:
            print("Accepted")
        break


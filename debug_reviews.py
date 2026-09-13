"""
Generate workforce_snapshot observations from brreg registry data.
For companies that have antallAnsatte > 0, create a workforce observation
from the official registry data.
"""
import json
import hashlib
from datetime import datetime, timezone

profiles = []
with open('out-all/profiles.jsonl', encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        profiles.append(json.loads(line))

# Check existing workforce coverage
existing_workforce_orgs = set()
for line in open('out-all/footprint_cache/brreg_observations.jsonl', encoding='utf-8'):
    if not line.strip(): continue
    obs = json.loads(line)
    if obs.get('signal_type') == 'workforce_snapshot':
        existing_workforce_orgs.add(str(obs['organisation_number']))

for line in open('out-all/footprint_cache/ocr_observations.jsonl', encoding='utf-8'):
    if not line.strip(): continue
    obs = json.loads(line)
    if obs.get('signal_type') == 'workforce_snapshot':
        existing_workforce_orgs.add(str(obs['organisation_number']))

print(f"Existing workforce orgs: {len(existing_workforce_orgs)}")

# Check how many profiles have employees data but no workforce observation
new_workforce = 0
for p in profiles:
    org = str(p['organisation_number'])
    if org in existing_workforce_orgs:
        continue
    employees = p.get('employees') or p.get('evidence', {}).get('registry_live', {}).get('value', {}).get('employees')
    if employees and int(employees) > 0:
        new_workforce += 1

print(f"Profiles with employees > 0 but no workforce obs: {new_workforce}")

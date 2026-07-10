#!/usr/bin/env python3
"""Accumulate Etihad's live fleet from airplanes.live (free, no key) into etihad_fleet.json.
Identifies Etihad by callsign ETD* AND UAE registration A6-*. Runs unattended in GitHub Actions."""
import json, os, time, urllib.request
from datetime import datetime, timezone

TYPES = ["A21N","A20N","A320","A321","A35K","A359","B789","B78X","B77W","B77L","A332","A333"]
OUT = "etihad_fleet.json"
UA = "etihad-fleet-sync/1.0 (personal SharePoint sync; contact: ops)"
# ICAO typecode -> friendly model (extend as needed)
MODEL = {"A21N":"A321neo","A20N":"A320neo","A320":"A320","A321":"A321","A35K":"A350-1000",
         "A359":"A350-900","B789":"787-9","B78X":"787-10","B77W":"777-300ER","B77L":"777-200LR/F",
         "A332":"A330-200","A333":"A330-300"}

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch(t):
    req = urllib.request.Request(f"https://api.airplanes.live/v2/type/{t}", headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("ac", [])
        except Exception as e:
            print(f"  {t} attempt {attempt+1} failed: {e}"); time.sleep(5*(attempt+1))
    return []

def main():
    fleet = {}
    if os.path.exists(OUT):
        fleet = {r["Title"]: r for r in json.load(open(OUT))}
    stamp = now(); new = 0
    for t in TYPES:
        for a in fetch(t):
            reg = str(a.get("r","")).upper().strip()
            cs  = str(a.get("flight","")).upper().strip()
            if not (reg.startswith("A6-") and cs.startswith("ETD")): continue
            tc = str(a.get("t","")).upper().strip() or t
            rec = fleet.get(reg)
            if rec is None:
                fleet[reg] = {"Title": reg, "Typecode": tc, "ICAO24": str(a.get("hex","")).upper(),
                              "Model": MODEL.get(tc, tc), "Operator": "Etihad Airways", "Active": True,
                              "FirstSeenUtc": stamp, "LastSeenUtc": stamp}
                new += 1
            else:
                rec.update(Typecode=tc, ICAO24=str(a.get("hex","")).upper() or rec.get("ICAO24",""),
                           Model=MODEL.get(tc, tc), Active=True, LastSeenUtc=stamp)
        time.sleep(2)  # respect ~1 req/sec
    # Soft-retire: any tail not seen in RETIRE_DAYS -> Active=false (never deleted)
    RETIRE_DAYS = 30
    cutoff = time.time() - RETIRE_DAYS*86400
    retired = 0
    for rec in fleet.values():
        seen = datetime.strptime(rec["LastSeenUtc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        if seen < cutoff and rec.get("Active", True):
            rec["Active"] = False; retired += 1
    rows = sorted(fleet.values(), key=lambda r: r["Title"])
    json.dump(rows, open(OUT,"w"), indent=2)
    active = sum(1 for r in rows if r["Active"])
    print(f"Sweep {stamp}: {len(rows)} tails ({active} active) | +{new} new, {retired} soft-retired this run")

if __name__ == "__main__":
    main()

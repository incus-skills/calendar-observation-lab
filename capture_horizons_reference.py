#!/usr/bin/env python3
"""Capture geocentric apparent Sun/Moon references from JPL Horizons (stdlib only)."""
from __future__ import annotations
import argparse, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
API_URL="https://ssd.jpl.nasa.gov/api/horizons.api"
DEFAULT_EPOCHS=["2026-02-03 12:00:00","2026-05-03 12:00:00","2026-08-03 12:00:00","2026-11-03 12:00:00"]
TARGETS={"sun":"10","moon":"301"}
def capture(name,target_id,epoch,timeout):
    params={"format":"text","COMMAND":target_id,"OBJ_DATA":"NO","MAKE_EPHEM":"YES","EPHEM_TYPE":"OBSERVER","CENTER":"500@399","TIME_TYPE":"UT","TLIST_TYPE":"CAL","TLIST":f"'{epoch}'","QUANTITIES":"31","ANG_FORMAT":"DEG","CSV_FORMAT":"YES","TIME_DIGITS":"SECONDS"}
    url=f"{API_URL}?{urlencode(params)}"
    try:
        with urlopen(Request(url,headers={"User-Agent":"calendar-observation-lab/0.2 (reference capture)"}),timeout=timeout) as response:
            body,status=response.read().decode("utf-8",errors="replace"),response.status
    except HTTPError as exc: raise RuntimeError(f"Horizons HTTP {exc.code} for {name}: {exc.read().decode('utf-8',errors='replace')}") from exc
    except URLError as exc: raise RuntimeError(f"Could not reach Horizons for {name}: {exc}") from exc
    meta={"target":name,"target_id":target_id,"endpoint":API_URL,"request_url":url,"parameters":params,"http_status":status,
      "captured_at_utc":datetime.now(timezone.utc).isoformat(),"epoch_interpretation":"nominal UTC civil timestamp supplied as UT to Horizons",
      "observer_origin":"Earth geocentre (500@399)","quantity_31_definition":"Observer-centred IAU76/80 ecliptic-of-date longitude/latitude; apparent position with light-time, gravitational deflection and stellar aberration."}
    return meta,body
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--epoch",action="append",dest="epochs",help="Repeatable; defaults to four discriminating epochs")
    p.add_argument("--output-dir",type=Path,default=Path("reference-data/horizons")); p.add_argument("--timeout",type=float,default=45.0)
    a=p.parse_args(); epochs=a.epochs or DEFAULT_EPOCHS
    for epoch in epochs:
        try: datetime.strptime(epoch,"%Y-%m-%d %H:%M:%S")
        except ValueError: p.error(f"Invalid epoch {epoch!r}; expected YYYY-MM-DD HH:MM:SS")
    if len(set(epochs))!=len(epochs): p.error("Epoch values must be unique")
    a.output_dir.mkdir(parents=True,exist_ok=True)
    for epoch in epochs:
        key=epoch[:10].replace("-",""); manifest={"baseline_id":"ORB-1","epoch":epoch,"epoch_scale_sent_to_horizons":"UT","requested_epoch_label":"nominal UTC","observer_origin":"Earth geocentre (500@399)","targets":{}}
        for name,target_id in TARGETS.items():
            print(f"Requesting {name} at {epoch}...",flush=True); meta,body=capture(name,target_id,epoch,a.timeout)
            stem=f"{key}_{name}"; raw=a.output_dir/f"{stem}.txt"; req=a.output_dir/f"{stem}.request.json"
            raw.write_text(body,encoding="utf-8"); req.write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
            manifest["targets"][name]={"raw_response":str(raw),"request_metadata":str(req)}
            print(f"----- BEGIN {name.upper()} {epoch} HORIZONS RESPONSE -----\n{body.rstrip()}\n----- END {name.upper()} {epoch} HORIZONS RESPONSE -----")
            time.sleep(1.0)
        dest=a.output_dir/f"ORB-1-{key}-manifest.json"; dest.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8"); print(f"Manifest: {dest}")
    print(f"Captured {len(epochs)} epochs with raw responses and request provenance."); return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except (RuntimeError,OSError) as exc: print(f"ERROR: {exc}",file=sys.stderr); raise SystemExit(1)

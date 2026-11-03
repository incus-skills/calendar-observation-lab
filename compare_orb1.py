#!/usr/bin/env python3
"""Bounded diagnostic comparison of libephemeris/Skyfield with Horizons ORB-1."""
from __future__ import annotations
import csv,hashlib,importlib.metadata,json
from datetime import datetime
from pathlib import Path
import libephemeris as eph
from libephemeris.constants import FLG_NONUT,FLG_SPEED,MOON,SUN
REF=Path("reference-data/horizons"); OUT=Path("results")
def parse_row(path):
    text=path.read_text(encoding="utf-8")
    if "$$SOE" not in text or "$$EOE" not in text: raise ValueError(f"Incomplete Horizons block: {path}")
    block=text.split("$$SOE",1)[1].split("$$EOE",1)[0]
    rows=[r for r in csv.reader(block.splitlines()) if r and any(x.strip() for x in r)]
    if len(rows)!=1: raise ValueError(f"Expected one data row in {path}; got {len(rows)}")
    vals=[float(v.strip()) for v in rows[0][1:] if v.strip()]
    if len(vals)!=2: raise ValueError(f"Expected longitude/latitude in {path}; got {vals!r}")
    return vals[0],vals[1]
def angle_diff(a,b): return (a-b+180.0)%360.0-180.0
def ephemeris_inventory():
    root=Path.home()/".cache"; found=[]
    if root.exists():
        for path in root.rglob("de*.bsp"):
            if path.is_file():
                h=hashlib.sha256()
                with path.open("rb") as f:
                    for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
                found.append({"path":str(path),"filename":path.name,"size_bytes":path.stat().st_size,"sha256":h.hexdigest()})
    return sorted(found,key=lambda x:x["path"])
def compare_one(manifest_path):
    m=json.loads(manifest_path.read_text(encoding="utf-8")); stamp=m["epoch"]; dt=datetime.strptime(stamp,"%Y-%m-%d %H:%M:%S")
    jd=float(eph.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60+dt.second/3600))
    ref={n:parse_row(REF/f"{dt:%Y%m%d}_{n}.txt") for n in ("sun","moon")}; ref_phase=(ref["moon"][0]-ref["sun"][0])%360.0
    bodies={"sun":SUN,"moon":MOON}; variants={}
    for label,flags in {"default":FLG_SPEED,"nonut":FLG_SPEED|FLG_NONUT}.items():
        pos={}; returned={}
        for name,body in bodies.items():
            values,ret=eph.calc_ut(jd,body,flags); pos[name]=list(values); returned[name]=int(ret)
        phase=(pos["moon"][0]-pos["sun"][0])%360.0
        variants[label]={"requested_flags":int(flags),"returned_flags":returned,
          "positions":{n:{"longitude_deg":pos[n][0],"latitude_deg":pos[n][1]} for n in bodies},
          "phase_elongation_deg":phase,
          "residuals_vs_horizons":{n:{"longitude_arcsec":angle_diff(pos[n][0],ref[n][0])*3600,"latitude_arcsec":(pos[n][1]-ref[n][1])*3600} for n in bodies},
          "phase_residual_arcsec":angle_diff(phase,ref_phase)*3600}
    return {"epoch":stamp,"julian_day_ut":jd,"reference":{n:{"longitude_deg":ref[n][0],"latitude_deg":ref[n][1]} for n in bodies},"reference_phase_elongation_deg":ref_phase,"variants":variants}
def main():
    manifests=sorted(REF.glob("ORB-1-*-manifest.json"))
    if not manifests: raise FileNotFoundError(f"No dated ORB-1 manifests in {REF}; run capture script")
    eph.set_calc_mode("skyfield"); mode=eph.get_calc_mode()
    if mode!="skyfield": raise RuntimeError(f"Could not force Skyfield; active mode={mode!r}")
    epochs=[compare_one(p) for p in manifests]
    report={"baseline_id":"ORB-1","reference_source":"JPL Horizons quantity 31; raw responses and request metadata retained",
      "implementation":{"package":"libephemeris","version":importlib.metadata.version("libephemeris"),"calculation_mode":mode,
        "backend_policy":"Skyfield forced explicitly; Horizons backend not selected","ephemeris_files_found_in_cache":ephemeris_inventory()},
      "epochs":epochs,"interpretation":{"status":"diagnostic_only","tolerance_deg":None,"note":"No numerical acceptance threshold is imposed. This bounded sample tests frame behaviour across epochs, not universal accuracy; Horizons and Skyfield may use different JPL ephemerides."}}
    OUT.mkdir(parents=True,exist_ok=True); dest=OUT/"ORB-1-comparison.json"; dest.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"Comparison written: {dest}\nlibephemeris {report['implementation']['version']} / {mode}")
    for e in epochs:
        print(f"\n=== {e['epoch']} | Horizons phase {e['reference_phase_elongation_deg']:.9f} deg ===")
        for label,r in e["variants"].items():
            print(f"[{label}]")
            for n in ("sun","moon"):
                d=r["residuals_vs_horizons"][n]; print(f"{n}: dLon={d['longitude_arcsec']:+.4f} arcsec dLat={d['latitude_arcsec']:+.4f} arcsec")
            print(f"phase residual={r['phase_residual_arcsec']:+.4f} arcsec")
    print("\nDiagnostic only; no tolerance asserted."); return 0
if __name__=="__main__": raise SystemExit(main())

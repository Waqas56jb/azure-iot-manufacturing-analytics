import csv
import json
import math
import random
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[2]
src = ROOT / "server" / "data" / "raw" / "dataset.csv"
rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))


def fnum(r, k):
    return float(r[k])


for r in rows:
    r["_air"] = fnum(r, "Air temperature [K]")
    r["_proc"] = fnum(r, "Process temperature [K]")
    r["_rpm"] = fnum(r, "Rotational speed [rpm]")
    r["_torque"] = fnum(r, "Torque [Nm]")
    r["_wear"] = fnum(r, "Tool wear [min]")
    r["_fail"] = int(r["Machine failure"])
    r["_temp_delta"] = r["_proc"] - r["_air"]
    if r["_wear"] >= 200 or r["_torque"] >= 60:
        r["_risk"] = "HIGH"
    elif r["_wear"] >= 120 or r["_torque"] >= 45:
        r["_risk"] = "MEDIUM"
    else:
        r["_risk"] = "LOW"
    codes = [c for c in ["TWF", "HDF", "PWF", "OSF", "RNF"] if r[c] == "1"]
    r["_ftype"] = codes[0] if codes else "NONE"

n = len(rows)
fails = [r for r in rows if r["_fail"] == 1]
fail_count = len(fails)

by_type = []
for t in ["L", "M", "H"]:
    subset = [r for r in rows if r["Type"] == t]
    fc = sum(r["_fail"] for r in subset)
    by_type.append(
        {
            "type": t,
            "label": {"L": "Low", "M": "Medium", "H": "High"}[t],
            "total": len(subset),
            "failures": fc,
            "failureRate": round(fc / len(subset) * 100, 2) if subset else 0,
            "avgTorque": round(mean(r["_torque"] for r in subset), 2),
            "avgRpm": round(mean(r["_rpm"] for r in subset), 1),
            "avgWear": round(mean(r["_wear"] for r in subset), 1),
            "avgAirTemp": round(mean(r["_air"] for r in subset), 2),
            "avgProcessTemp": round(mean(r["_proc"] for r in subset), 2),
        }
    )

failure_types = []
for code, name in [
    ("TWF", "Tool Wear"),
    ("HDF", "Heat Dissipation"),
    ("PWF", "Power"),
    ("OSF", "Overstrain"),
    ("RNF", "Random"),
]:
    c = sum(1 for r in rows if r[code] == "1")
    failure_types.append(
        {
            "code": code,
            "name": name,
            "count": c,
            "shareOfFailures": round(c / fail_count * 100, 1) if fail_count else 0,
        }
    )

risk = []
for band in ["LOW", "MEDIUM", "HIGH"]:
    subset = [r for r in rows if r["_risk"] == band]
    fc = sum(r["_fail"] for r in subset)
    risk.append(
        {
            "band": band,
            "total": len(subset),
            "failures": fc,
            "failureRate": round(fc / len(subset) * 100, 2) if subset else 0,
        }
    )

wear_bins = []
for a, b in zip(range(0, 280, 40), range(40, 321, 40)):
    subset = [r for r in rows if a <= r["_wear"] < b]
    fc = sum(r["_fail"] for r in subset)
    wear_bins.append(
        {
            "range": f"{a}-{b}",
            "total": len(subset),
            "failures": fc,
            "failureRate": round(fc / max(len(subset), 1) * 100, 2),
        }
    )

torque_bins = []
tedges = [0, 15, 30, 45, 60, 80]
for i in range(len(tedges) - 1):
    a, b = tedges[i], tedges[i + 1]
    subset = [r for r in rows if a <= r["_torque"] < b]
    fc = sum(r["_fail"] for r in subset)
    torque_bins.append(
        {
            "range": f"{a}-{b}",
            "total": len(subset),
            "failures": fc,
            "failureRate": round(fc / max(len(subset), 1) * 100, 2),
        }
    )

td_bins = []
for a, b in [(7, 8), (8, 9), (9, 10), (10, 11), (11, 12)]:
    subset = [r for r in rows if a <= r["_temp_delta"] < b]
    fc = sum(r["_fail"] for r in subset)
    td_bins.append(
        {
            "range": f"{a}-{b}K",
            "total": len(subset),
            "failures": fc,
            "failureRate": round(fc / max(len(subset), 1) * 100, 2),
        }
    )

rpm_bins = []
for a, b in [(1100, 1400), (1400, 1600), (1600, 1800), (1800, 2200), (2200, 3000)]:
    subset = [r for r in rows if a <= r["_rpm"] < b]
    fc = sum(r["_fail"] for r in subset)
    vals = [r["_torque"] for r in subset]
    rpm_bins.append(
        {
            "range": f"{a}-{b}",
            "total": len(subset),
            "failures": fc,
            "failureRate": round(fc / max(len(subset), 1) * 100, 2),
            "avgTorque": round(mean(vals), 2) if vals else 0,
        }
    )

random.seed(42)
sample = fails + random.sample([r for r in rows if r["_fail"] == 0], 400)
scatter = [
    {
        "rpm": round(r["_rpm"], 1),
        "torque": round(r["_torque"], 2),
        "wear": round(r["_wear"], 1),
        "failed": bool(r["_fail"]),
        "type": r["Type"],
        "failureType": r["_ftype"],
    }
    for r in sample
]

top_failures = sorted(fails, key=lambda r: r["_wear"], reverse=True)[:12]
top_table = [
    {
        "udi": int(float(r["UDI"])),
        "productId": r["Product ID"],
        "type": r["Type"],
        "failureType": r["_ftype"],
        "risk": r["_risk"],
        "wear": round(r["_wear"], 1),
        "torque": round(r["_torque"], 2),
        "rpm": round(r["_rpm"], 1),
        "tempDelta": round(r["_temp_delta"], 2),
    }
    for r in top_failures
]

fail_mix = []
for t in ["L", "M", "H"]:
    subset = [r for r in fails if r["Type"] == t]
    row = {"type": t}
    for code in ["TWF", "HDF", "PWF", "OSF", "RNF"]:
        row[code] = sum(1 for r in subset if r[code] == "1")
    fail_mix.append(row)

out = {
    "meta": {
        "title": "ForgeSight",
        "subtitle": "Manufacturing IoT Operations Analytics",
        "records": n,
        "generatedFrom": "AI4I predictive maintenance telemetry",
    },
    "kpis": {
        "totalRecords": n,
        "failures": fail_count,
        "failureRate": round(fail_count / n * 100, 2),
        "healthyRate": round((n - fail_count) / n * 100, 2),
        "avgTorque": round(mean(r["_torque"] for r in rows), 2),
        "avgRpm": round(mean(r["_rpm"] for r in rows), 1),
        "avgToolWear": round(mean(r["_wear"] for r in rows), 1),
        "avgTempDelta": round(mean(r["_temp_delta"] for r in rows), 2),
        "medianWearFailures": round(median(r["_wear"] for r in fails), 1) if fails else 0,
        "highRiskShare": round(sum(1 for r in rows if r["_risk"] == "HIGH") / n * 100, 2),
    },
    "byProductType": by_type,
    "failureTypes": failure_types,
    "riskBands": risk,
    "wearBins": wear_bins,
    "torqueBins": torque_bins,
    "tempDeltaBins": td_bins,
    "rpmBins": rpm_bins,
    "failureMixByType": fail_mix,
    "scatter": scatter,
    "topFailures": top_table,
    "insights": [
        f"Overall machine failure rate is {round(fail_count / n * 100, 2)}% across {n:,} telemetry records.",
        "Heat dissipation (HDF) and overstrain (OSF) are the leading failure modes.",
        f"High-risk operating conditions account for {round(sum(1 for r in rows if r['_risk']=='HIGH') / n * 100, 2)}% of cycles but concentrate most failures.",
        "Tool wear and elevated torque show the strongest association with failure spikes in aggregate bins.",
    ],
}

out_path = ROOT / "client" / "public" / "data" / "analytics.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out), encoding="utf-8")
print("wrote", out_path, "bytes", out_path.stat().st_size)

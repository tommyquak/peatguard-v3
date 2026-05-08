"""Idempotent seed loader for the demo ledger.

Mirrors the fixtures embedded in the design handoff so the freshly seeded
backend matches the screenshots in ``design_handoff_peatguard``:

- AOIs come from ``web-screens-1.jsx:160-166``
- Workers come from ``web-screens-2.jsx:328-334``
- Tasks come from ``PeatGuard Prototype.html:31-36``
"""

from __future__ import annotations

import json
import logging

from peatguard.api.db import connect

logger = logging.getLogger(__name__)


AOIS = [
    # code, name, risk, pct_critical, refresh, progress, restored, area, lat, lng
    ("SBG-C", "Sebangau Block C", 0.71, 18.4, "2026-05-04", 34, 412, 12_400, -2.342, 113.911),
    ("MWE-1", "Mawas East",        0.58, 11.2, "2026-05-04", 62, 880,  8_900, -2.220, 114.450),
    ("BBS-2", "Berbak-Sembilang",  0.49,  7.8, "2026-05-03", 22, 240, 18_200, -1.500, 104.080),
    ("PSG-1", "Padang Sugihan",    0.66, 14.0, "2026-05-03", 48, 540,  6_700, -2.870, 105.350),
    ("KPN-3", "Kampar Peninsula N",0.81, 24.1, "2026-05-02", 11,  90, 22_500,  0.450, 102.170),
    ("SGP-1", "Sungai Putri",      0.42,  6.4, "2026-05-02", 71,1_120,  5_300, -1.090, 110.180),
]

VILLAGES = [
    ("vil-hampangen", "Hampangen Jaya", "SBG-C", -2.341, 113.911),
    ("vil-pangkoh",   "Pangkoh Hilir",  "MWE-1", -2.221, 114.448),
    ("vil-bukitbatu", "Bukit Batu",     "KPN-3",  0.451, 102.171),
    ("vil-sgputri",   "Sungai Putri",   "SGP-1", -1.091, 110.181),
]

WORKERS = [
    # id, name, village_id, nik_verified, rating, role, total_paid, completion_rate, tasks_done, flag
    ("w-sumardi",  "Sumardi Budiman",  "vil-hampangen", 1, 4.8, "team_lead", 8_750_000, 95, 38, None),
    ("w-rina",     "Rina Anggraini",   "vil-pangkoh",   1, 4.7, None,        4_120_000, 92, 21, None),
    ("w-joko",     "Joko Pramono",     "vil-hampangen", 1, 4.5, None,        6_440_000, 87, 29, None),
    ("w-siti",     "Siti Rahmawati",   "vil-bukitbatu", 0, 4.4, None,        2_260_000, 82, 12, None),
    ("w-agus",     "Agus Wijaya",      "vil-pangkoh",   1, 4.2, None,        9_980_000, 78, 47, "velocity"),
    ("w-toni",     "Toni Hidayat",     "vil-bukitbatu", 1, 4.9, None,        3_960_000, 100, 18, None),
    ("w-maria",    "Maria Sinaga",     "vil-sgputri",   1, 4.6, "team_lead", 7_020_000, 91, 33, None),
]

TASKS = [
    # id, aoi, village, type, title, sub, payout, deadline, status, worker_id, rail, deliverables
    ("C-04", "SBG-C", "vil-hampangen", "canal_block",
     "Block canal at C-04 mouth", "0.42 ha · needs 3 photos + GPS",
     250_000, "2026-05-18T17:00", "available", None, "DANA",
     ["3 photos: before, during, after canal block",
      "GPS track of dam edge (>= 8 m linear)",
      "Timestamp within working window 06:00-17:00 WIB",
      "Voice note: rationale for blockage"]),
    ("M-12", "MWE-1", "vil-pangkoh", "revegetation",
     "Replant plot 12", "1 ha · seedlings provided",
     180_000, "2026-05-20T17:00", "available", None, "BRI direct",
     ["Photos of seedlings planted (3+)",
      "GPS perimeter walk of plot",
      "Headcount of seedlings"]),
    ("F-B",  "KPN-3", "vil-bukitbatu", "patrol",
     "Fire patrol sector B", "Afternoon shift 14:00-20:00",
     150_000, "2026-05-08T20:00", "available", None, "PT Pos cash",
     ["GPS track for full route",
      "Photos at 4 checkpoints",
      "Voice note of any incidents"]),
    ("C-02", "SBG-C", "vil-hampangen", "canal_block",
     "Block canal C-02", "Earlier dam, awaiting validation",
     250_000, "2026-05-02T17:00", "submitted", "w-sumardi", "DANA",
     ["3 photos: before, during, after canal block",
      "GPS track of dam edge (>= 8 m linear)",
      "Timestamp within working window 06:00-17:00 WIB"]),
    ("C-01", "SBG-C", "vil-hampangen", "canal_block",
     "Block canal C-01", "Completed and paid",
     250_000, "2026-04-28T17:00", "paid", "w-sumardi", "DANA",
     ["3 photos: before, during, after canal block",
      "GPS track of dam edge (>= 8 m linear)"]),
]

SUBMITTED_PHOTO_FIXTURES = {
    # task_id -> list of (phase, ts, lat, lng, accuracy_m, sha256, prev_sha256)
    "C-02": [
        ("before", 1714801320000, -2.34132, 113.91085, 8.4, "a"*64, None),
        ("during", 1714810680000, -2.34134, 113.91082, 7.9, "b"*64, "a"*64),
        ("after",  1714820100000, -2.34130, 113.91087, 8.1, "c"*64, "b"*64),
    ],
}

SEED_PAYMENTS = [
    # id, task_id, worker_id, amount, rail, status
    ("pay-c01-sumardi", "C-01", "w-sumardi", 250_000, "DANA", "released"),
]

SEED_MESSAGES = [
    # task_id, sender, body, kind, attach
    ("C-02", "Nadia Arifin", "Pak Sumardi, the during & after photos look great. The before photo is a bit blurry — can you reshoot it?", "operator", None),
    ("C-02", "Nadia Arifin", "", "operator", "P-01 before · blurry"),
]


def seed_if_empty() -> None:
    """Insert demo fixtures if the AOI table is empty. Idempotent."""
    with connect() as conn:
        existing = conn.execute("SELECT COUNT(*) AS c FROM aois").fetchone()["c"]
        if existing > 0:
            logger.info("ledger already seeded (%d aois) -- skipping", existing)
            return
        logger.info("seeding ledger with demo fixtures")
        conn.executemany(
            "INSERT INTO aois (code,name,risk,pct_critical,refresh_date,progress_pct,restored_ha,area_ha,center_lat,center_lng) VALUES (?,?,?,?,?,?,?,?,?,?)",
            AOIS,
        )
        conn.executemany(
            "INSERT INTO villages (id,name,aoi_code,lat,lng) VALUES (?,?,?,?,?)",
            VILLAGES,
        )
        conn.executemany(
            "INSERT INTO workers (id,name,village_id,nik_verified,rating,role,total_paid,completion_rate,tasks_done,flag) VALUES (?,?,?,?,?,?,?,?,?,?)",
            WORKERS,
        )
        for (tid, aoi, vil, ttype, title, sub, payout, deadline, status, worker, rail, delivs) in TASKS:
            submitted_at = "2026-05-04T11:53:00" if status in ("submitted", "approved", "paid") else None
            conn.execute(
                """INSERT INTO tasks (id, aoi_code, village_id, type, title, sub, payout_idr, deadline,
                                       status, worker_id, deliverables_json, rail, submitted_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid, aoi, vil, ttype, title, sub, payout, deadline, status, worker,
                 json.dumps(delivs), rail, submitted_at),
            )
        for tid, photos in SUBMITTED_PHOTO_FIXTURES.items():
            for (phase, ts, lat, lng, acc, sha, prev) in photos:
                conn.execute(
                    "INSERT INTO photos (task_id, phase, ts, lat, lng, accuracy_m, sha256, prev_sha256) VALUES (?,?,?,?,?,?,?,?)",
                    (tid, phase, ts, lat, lng, acc, sha, prev),
                )
        for (pid, tid, wid, amt, rail, status) in SEED_PAYMENTS:
            conn.execute(
                "INSERT INTO payments (id, task_id, worker_id, amount, rail, status, released_at) VALUES (?,?,?,?,?,?,datetime('now'))",
                (pid, tid, wid, amt, rail, status),
            )
        for (tid, sender, body, kind, attach) in SEED_MESSAGES:
            conn.execute(
                "INSERT INTO messages (task_id, sender, body, kind, attach) VALUES (?,?,?,?,?)",
                (tid, sender, body, kind, attach),
            )
        logger.info("seed complete: %d aois · %d workers · %d tasks", len(AOIS), len(WORKERS), len(TASKS))

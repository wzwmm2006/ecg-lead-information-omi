"""Runner for the authorized 20 A2a fits. Sequential, resumable, output-isolated.

No A1 tasks. No hidden TEST. No STAFF III. Stops on first failure and preserves logs.
"""
from __future__ import annotations
import json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

GATE = Path(__file__).resolve().parent
RUN = GATE / "runs" / "RUN_20261110_A2a_ONLY"
LOG = RUN / "train.log"
ERR = RUN / "train.error.log"
EXEC = GATE / "run_a2a_fit.py"
CONFIGS = ["C0", "C1", "C2", "C3"]


def main() -> None:
    tasks = [(f, c) for f in range(5) for c in CONFIGS]
    if len(tasks) != 20:
        raise SystemExit("wrong task count")
    with open(RUN / "TASK_PLAN.csv", "w", newline="", encoding="utf-8") as fh:
        import csv
        w = csv.writer(fh)
        w.writerow(["index", "outer_fold", "configuration", "seed"])
        for i, (f, c) in enumerate(tasks, 1):
            w.writerow([i, f, c, 20260813 + f + 100 * CONFIGS.index(c)])
    log = open(LOG, "a", encoding="utf-8")
    err = open(ERR, "a", encoding="utf-8")
    completed = 0
    for index, (fold, cfg) in enumerate(tasks, 1):
        metrics = RUN / f"fold{fold}" / "A2a" / f"{cfg}_metrics.csv"
        if metrics.exists():
            log.write(f"{datetime.now(timezone.utc).isoformat()} SKIP_EXISTING fold={fold} cfg={cfg}\n")
            log.flush()
            completed += 1
            continue
        log.write(f"{datetime.now(timezone.utc).isoformat()} START [{index}/20] A2a fold={fold} cfg={cfg}\n")
        log.flush()
        start = time.time()
        completed_proc = subprocess.run(
            [sys.executable, str(EXEC), "--outer-fold", str(fold), "--config", cfg, "--run-root", str(RUN)],
            cwd=str(GATE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        )
        log.write(completed_proc.stdout or "")
        log.flush()
        if completed_proc.returncode != 0:
            err.write(f"{datetime.now(timezone.utc).isoformat()} FAIL [{index}/20] fold={fold} cfg={cfg} exit={completed_proc.returncode} elapsed={time.time()-start:.1f}s\n")
            err.flush()
            print(f"FAIL fold={fold} cfg={cfg} exit={completed_proc.returncode}")
            raise SystemExit(1)
        log.write(f"{datetime.now(timezone.utc).isoformat()} DONE [{index}/20] fold={fold} cfg={cfg} elapsed={time.time()-start:.1f}s\n")
        log.flush()
        completed += 1
    log.write(f"{datetime.now(timezone.utc).isoformat()} ALL_DONE completed={completed}/20\n")
    log.close(); err.close()
    print(f"ALL_DONE completed={completed}/20")


if __name__ == "__main__":
    main()

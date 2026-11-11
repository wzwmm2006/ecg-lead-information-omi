from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GATE = Path(__file__).resolve().parent
RUN = GATE / "runs" / "RUN_20261110_A1A2a"
LOG = RUN / "train.log"
ERR = RUN / "train.error.log"
PY = sys.executable


def main() -> None:
    import csv
    with open(RUN / "TASK_PLAN.csv", newline="", encoding="utf-8") as fh:
        tasks = list(csv.DictReader(fh))
    if len(tasks) != 60:
        raise SystemExit(f"unexpected task count {len(tasks)}")
    with open(LOG, "a", encoding="utf-8") as log:
        for index, task in enumerate(tasks, 1):
            analysis = task["analysis"]
            fold = task["outer_fold"]
            config = task["configuration"]
            metrics = RUN / f"fold{fold}" / analysis / f"{config}_metrics.csv"
            if metrics.exists():
                log.write(f"{datetime.now(timezone.utc).isoformat()} SKIP_EXISTING {analysis} fold={fold} cfg={config}\n")
                continue
            log.write(f"{datetime.now(timezone.utc).isoformat()} START [{index}/60] {analysis} fold={fold} cfg={config}\n")
            log.flush()
            cmd = [PY, str(GATE / "run_fit.py"), "--analysis", analysis, "--outer-fold", fold, "--config", config, "--run-root", str(RUN)]
            completed = subprocess.run(cmd, cwd=str(GATE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            log.write(completed.stdout or "")
            log.flush()
            if completed.returncode != 0:
                with open(ERR, "a", encoding="utf-8") as err:
                    err.write(f"{datetime.now(timezone.utc).isoformat()} FAIL [{index}/60] {analysis} fold={fold} cfg={config} exit={completed.returncode}\n")
                raise SystemExit(f"fit failed: {analysis} fold={fold} {config}")
            log.write(f"{datetime.now(timezone.utc).isoformat()} DONE [{index}/60] {analysis} fold={fold} cfg={config}\n")
            log.flush()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import subprocess
from pathlib import Path
import logging
import csv
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# -----------------------------
# CONFIG
# -----------------------------
VINA_EXE = "vina-gpu"              # GPU-enabled Vina executable
RECEPTOR_DIR = Path("./")
LIGAND_DIR = Path("./")
OUT_DIR = Path("./docking_results")
CONF_DIR = Path("./generated_conf")  # folder to store generated config files
OVERWRITE = False
TIMEOUT = None
SUMMARY_FILE = OUT_DIR / "docking_summary.csv"

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def detect_gpus():
    """Detect number of GPUs using nvidia-smi"""
    try:
        result = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, check=True)
        gpus = [line.split()[1].rstrip(":") for line in result.stdout.strip().splitlines()]
        logging.info(f"Detected GPUs: {gpus}")
        return list(range(len(gpus)))
    except Exception:
        logging.warning("No GPUs detected or nvidia-smi not found. Defaulting to GPU 0")
        return [0]

def generate_conf(base_conf_path, receptor_path, ligand_path, out_path):
    """Generate config file with space after '='"""
    lines = base_conf_path.read_text().splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("receptor="):
            new_lines.append(f"receptor= {receptor_path.name}")
        elif stripped.startswith("ligand="):
            new_lines.append(f"ligand= {ligand_path.name}")
        elif stripped.startswith("out="):
            new_lines.append(f"out= {out_path.name}")
        else:
            new_lines.append(line)
    CONF_DIR.mkdir(exist_ok=True)
    conf_file = CONF_DIR / f"conf_{receptor_path.stem}_{ligand_path.stem}.txt"
    conf_file.write_text("\n".join(new_lines))
    return conf_file

def run_vina(conf_file, gpu_id):
    """Run vina on a specific GPU"""
    cmd = [VINA_EXE, "--config", str(conf_file), "--gpu_id", str(gpu_id)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    return result.returncode, result.stdout, result.stderr

def dock_pair(receptor_path, base_conf_path, ligand_path, gpu_id):
    """Dock one receptor-ligand pair on specified GPU"""
    out_file = OUT_DIR / f"{receptor_path.stem}_{ligand_path.stem}_out.pdbqt"
    if out_file.exists() and not OVERWRITE:
        logging.info(f"SKIP: {out_file.name}")
        return {
            "receptor": receptor_path.stem,
            "ligand": ligand_path.stem,
            "out_file": out_file.name,
            "status": "skipped",
            "timestamp": datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        }

    conf_file = generate_conf(base_conf_path, receptor_path, ligand_path, out_file)
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    try:
        logging.info(f"RUNNING: {receptor_path.stem} + {ligand_path.stem} on GPU {gpu_id}")
        rc, out, err = run_vina(conf_file, gpu_id)

        log_base = OUT_DIR / f"{receptor_path.stem}_{ligand_path.stem}_vina_{timestamp}"
        (log_base.with_suffix(".stdout.txt")).write_text(out)
        (log_base.with_suffix(".stderr.txt")).write_text(err)

        status = "success" if rc == 0 else "failed"
        logging.info(f"{status.upper()}: {out_file.name}")

    except subprocess.TimeoutExpired:
        logging.error(f"TIMEOUT: {out_file.name}")
        status = "timeout"
    except Exception:
        logging.exception(f"ERROR: {out_file.name}")
        status = "error"

    return {
        "receptor": receptor_path.stem,
        "ligand": ligand_path.stem,
        "out_file": out_file.name,
        "status": status,
        "timestamp": timestamp
    }

# -----------------------------
# MAIN
# -----------------------------
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    OUT_DIR.mkdir(exist_ok=True)
    CONF_DIR.mkdir(exist_ok=True)

    gpus = detect_gpus()

    receptors = sorted(RECEPTOR_DIR.glob("receptor_*.pdbqt"))
    ligands = sorted(LIGAND_DIR.glob("lig_*.pdbqt"))

    if not receptors or not ligands:
        logging.error("No receptors or ligands found.")
        return

    # Build all receptor-ligand pairs
    tasks = []
    for i, (receptor) in enumerate(receptors):
        base_conf_path = RECEPTOR_DIR / f"conf_{receptor.stem}.txt"
        if not base_conf_path.exists():
            logging.warning(f"No base config for {receptor.name}, skipping")
            continue
        for ligand in ligands:
            # Assign GPU in round-robin fashion
            gpu_id = gpus[(i * len(ligands) + ligands.index(ligand)) % len(gpus)]
            tasks.append((receptor, base_conf_path, ligand, gpu_id))

    summary_rows = []

    logging.info(f"Starting multi-GPU docking with {len(gpus)} GPUs ({len(tasks)} pairs)")
    with ThreadPoolExecutor(max_workers=len(gpus)) as executor:
        future_to_pair = {executor.submit(dock_pair, r, c, l, g): (r, l, g) for r, c, l, g in tasks}
        for future in as_completed(future_to_pair):
            result = future.result()
            summary_rows.append(result)

    summary_headers = ["receptor", "ligand", "out_file", "status", "timestamp"]
    with SUMMARY_FILE.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=summary_headers)
        writer.writeheader()
        writer.writerows(summary_rows)

    logging.info(f"GPU docking finished. Summary saved to {SUMMARY_FILE}")

if __name__ == "__main__":
    main()

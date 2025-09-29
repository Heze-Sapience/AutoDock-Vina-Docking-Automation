#!/usr/bin/env python3
import subprocess
from pathlib import Path
import logging
import csv
import datetime

# -----------------------------
# CONFIG
# -----------------------------
VINA_EXE = "vina"
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
def generate_conf(base_conf_path, receptor_path, ligand_path, out_path):
    """
    Create a corrected config file for one receptor-ligand pair:
    - fills receptor, ligand, out
    - ensures a space after '='
    - keeps all other parameters unchanged
    """
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
            new_lines.append(line)  # keep everything else unchanged

    CONF_DIR.mkdir(exist_ok=True)
    conf_file = CONF_DIR / f"conf_{receptor_path.stem}_{ligand_path.stem}.txt"
    conf_file.write_text("\n".join(new_lines))
    return conf_file

def run_vina(conf_file):
    """Run vina with a given config file"""
    result = subprocess.run([VINA_EXE, "--config", str(conf_file)],
                            capture_output=True, text=True,
                            timeout=TIMEOUT)
    return result.returncode, result.stdout, result.stderr

# -----------------------------
# MAIN
# -----------------------------
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    OUT_DIR.mkdir(exist_ok=True)
    CONF_DIR.mkdir(exist_ok=True)

    receptors = sorted(RECEPTOR_DIR.glob("receptor_*.pdbqt"))
    ligands = sorted(LIGAND_DIR.glob("lig_*.pdbqt"))

    if not receptors or not ligands:
        logging.error("No receptors or ligands found.")
        return

    summary_rows = []

    for receptor in receptors:
        base_conf_path = RECEPTOR_DIR / f"conf_{receptor.stem}.txt"
        if not base_conf_path.exists():
            logging.warning(f"No base config found for {receptor.name}, skipping")
            continue

        for ligand in ligands:
            out_file = OUT_DIR / f"{receptor.stem}_{ligand.stem}_out.pdbqt"
            if out_file.exists() and not OVERWRITE:
                logging.info(f"SKIP: {out_file.name}")
                summary_rows.append({
                    "receptor": receptor.stem,
                    "ligand": ligand.stem,
                    "out_file": out_file.name,
                    "status": "skipped",
                    "timestamp": datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
                })
                continue

            # generate config for this pair
            conf_file = generate_conf(base_conf_path, receptor, ligand, out_file)
            timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
            try:
                logging.info(f"RUNNING: receptor={receptor.stem}, ligand={ligand.stem}")
                rc, out, err = run_vina(conf_file)

                # save stdout/stderr logs
                log_base = OUT_DIR / f"{receptor.stem}_{ligand.stem}_vina_{timestamp}"
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

            summary_rows.append({
                "receptor": receptor.stem,
                "ligand": ligand.stem,
                "out_file": out_file.name,
                "status": status,
                "timestamp": timestamp
            })

    # write summary CSV
    summary_headers = ["receptor", "ligand", "out_file", "status", "timestamp"]
    with SUMMARY_FILE.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=summary_headers)
        writer.writeheader()
        writer.writerows(summary_rows)

    logging.info(f"Docking finished. Summary saved to {SUMMARY_FILE}")

if __name__ == "__main__":
    main()

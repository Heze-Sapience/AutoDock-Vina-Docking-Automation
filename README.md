# AutoDock Vina Docking Automation

This repository automates molecular docking using **AutoDock Vina**, supporting multiple execution modes:

* Sequential CPU
* CPU Parallel
* Single-GPU Parallel
* Multi-GPU Parallel

It automatically generates configuration files with **space after `=`** for each receptor–ligand pair, logs output, and summarizes results in a CSV.

---

## Features

* Config files automatically generated for each receptor-ligand pair.
* Maintains all original parameters (center, size, exhaustiveness).
* Supports sequential, CPU-parallel, single-GPU, and multi-GPU execution.
* Logs stdout/stderr separately for each docking.
* Summary CSV with status for all receptor–ligand pairs.

---
## Required installation
Linux:
Install vina into your base using the following command.
sudo apt install autodock-vina

Windows:
Download Miniconda app and install it. Run the script on the Miniconda prompt

---
## Directory Structure

```
project/
¦
+-- receptor_*.pdbqt         # Receptor files
+-- lig_*.pdbqt              # Ligand files
+-- conf_receptor_*.txt      # Base config placeholders
+-- docking_results/         # Docking outputs and logs
+-- generated_conf/          # Generated config files
+-- vina_sequential_cpu.py   # Sequential CPU script
+-- vina_parallel_cpu.py     # CPU-parallel script
+-- vina_single_gpu.py       # Single-GPU parallel script
+-- vina_multi_gpu.py        # Multi-GPU parallel script
+-- README.md
```

---

## Base Configuration File

Example: `conf_receptor_1.txt`

```
receptor=
ligand=
out=

center_x= -15.184
center_y= 6.127
center_z= 2.175

size_x= 126
size_y= 126
size_z= 126

exhaustiveness= 8

spacing= 0.5
```

* Script fills in `receptor=`, `ligand=`, and `out=` automatically.
* Other parameters remain unchanged.

---

## Usage Examples

Suppose you have:

```
receptor_1.pdbqt
receptor_2.pdbqt
lig_10.pdbqt
lig_11.pdbqt
conf_receptor_1.txt
conf_receptor_2.txt
```

---

### 1. Sequential CPU

```bash
python vina_sequential_cpu.py
```

* Runs **one receptor-ligand pair at a time**.
* Low-spec machines or testing purposes.
* Outputs and logs stored in `docking_results/`.
* Summary CSV: `docking_summary.csv`.

---

### 2. CPU Parallel

```bash
python vina_parallel_cpu.py
```

* Uses multiple **CPU threads** to run dockings in parallel.
* Assigns multiple receptor–ligand pairs to different threads.
* Suitable for high-spec CPUs without GPU.
* Logs and outputs same as sequential version.

---

### 3. Single-GPU Parallel

```bash
python vina_single_gpu.py
```

* Runs multiple receptor–ligand pairs concurrently on **one GPU**.
* Each pair gets its own config file in `generated_conf/`.
* Logs stdout/stderr separately; outputs in `docking_results/`.

---

### 4. Multi-GPU Parallel

```bash
python vina_multi_gpu.py
```

* Automatically detects **all available GPUs** via `nvidia-smi`.
* Distributes docking jobs across GPUs in **round-robin fashion**.
* Each GPU runs one docking at a time to prevent conflicts.
* Outputs, logs, and summary CSV saved in `docking_results/`.

---

## Output Structure

`docking_results/` contains:

```
receptor_1_lig_10_out.pdbqt
receptor_1_lig_10_vina_20250918T203000.stdout.txt
receptor_1_lig_10_vina_20250918T203000.stderr.txt
docking_summary.csv
```

* **Summary CSV columns**: `receptor, ligand, out_file, status, timestamp`.

---

## Configuration Options

Edit variables at the top of each script:

```python
VINA_EXE = "vina"              # Vina or GPU-enabled Vina executable
RECEPTOR_DIR = Path("./")
LIGAND_DIR = Path("./")
OUT_DIR = Path("./docking_results")
CONF_DIR = Path("./generated_conf")
OVERWRITE = False
TIMEOUT = None                 # seconds
GPU_ID = 0                     # single-GPU version only
MAX_WORKERS = number_of_threads # CPU parallel or GPU threads
```

* Multi-GPU script detects GPUs automatically.

---

## Notes

* Filenames for receptors and ligands must match base config placeholders.
* Config files are generated automatically with **space after `=`**.
* Use sequential or CPU-parallel scripts for machines without GPU.
* Use GPU scripts for faster execution on GPU-enabled machines.

---

## License

Released under **MIT License**.

---



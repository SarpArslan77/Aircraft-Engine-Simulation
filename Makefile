#* ======= Aircraft Engine HIL Digital Twin =======

# Toolchain Configuration.
PYTHON ?= python

# Synthesis & Frequency Timing Parameters [ns].
TARGET_PERIOD ?=
SWEEP_LOW_PERIOD ?=
SWEEP_HIGH_PERIOD ?=

.DEFAULT_GOAL := help

.PHONY: help sim synth sweep lint clean

help: ## Displays formatted target list and documentation.
	@$(PYTHON) -c "import re; print('\nAircraft Engine Simulator - Hardware-in-the-Loop Emulation Build Menu\n' + '='*70); [print(f'  \033[36m{m.group(1):<14}\033[0m {m.group(2).strip()}') for l in open('Makefile') if (m := re.match(r'^([a-zA-Z_-]+):.*?## (.*)', l))]; print('\nParameter Overrides:\n  make synth TARGET_PERIOD=8.5\n  make sweep SWEEP_LOW_PERIOD=1.5 SWEEP_HIGH_PERIOD=8.0\n')"

sim: ## Runs floating & fixed-point models and Cocotb hardware co-simulation.
	$(PYTHON) main.py

synth: ## Executes Out-of-Context (OOC) Vivado synthesis.
ifdef TARGET_PERIOD
	$(PYTHON) main.py --synth $(TARGET_PERIOD)
else
	$(PYTHON) main.py --synth
endif

sweep: ## Performs binary search clock frequency sweep.
ifneq ($(and $(SWEEP_LOW_PERIOD),$(SWEEP_HIGH_PERIOD)),)
	$(PYTHON) main.py --sweep $(SWEEP_LOW_PERIOD) $(SWEEP_HIGH_PERIOD)
else
	$(PYTHON) main.py --sweep
endif

lint: ## Runs Ruff and Verible linters.
	$(PYTHON) main.py --lint

clean: ## Removes transient simulation builds, Vivado logs and test artifacts.
	@echo Cleaning transient build and verification artifacts...
	@$(PYTHON) -c "import shutil, pathlib, glob; shutil.rmtree('sim_build', ignore_errors=True); [pathlib.Path(p).unlink(missing_ok=True) for p in glob.glob('*.log') + glob.glob('*.jou') + glob.glob('build_synth/*.log') + glob.glob('build_synth/*.jou') + ['results.xml']]"
	@echo Clean completed successfully.
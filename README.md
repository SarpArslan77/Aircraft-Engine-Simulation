# Real-Time Jet Engine Simulator on FPGA (Hardware-in-the-Loop Emulation)

This project implements a synthesizable, real-time mathematical model of a single-spool turbojet engine designed for **Hardware-in-the-Loop (HIL) emulation** (*Echtzeitsimulation*) on an FPGA. By solving thermodynamic and mechanical differential equations directly in hardware at discrete time steps ($dt = 1\text{ ms}$), the simulator acts as an exact digital twin to verify Engine Control Units (ECUs) without physical engine test cells.

The engine dynamics track key physical states—**Rotational Speed ($N$)**, **Compressor Outlet Pressure ($P$)**, and **Exhaust Gas Temperature ($EGT$)**—driven by the control input **Fuel Flow ($W_f$)**.

---

## Key Engineering Highlights

* **Physics-Based Dynamics:** Solves continuous-time engine non-linear differential equations using first-order forward Euler integration ($dt = 1\text{ ms}$).
* **Fixed-Point Arithmetic (*Festkomma-Arithmetik*):** Custom $Q16.16$ bit-true implementation with zero hardware dividers; division operations are replaced with pre-scaled fractional constants to conserve DSP slices and maximize clock frequencies.
* **Deterministic Safety Clamping:** Custom hardware saturation logic prevents binary wrap-around overflow and enforces physical engine lower bounds ($N \ge 0$, $P \ge P_{\text{amb}}$, $T \ge T_{\text{amb}}$).
* **Memory-Mapped Register Map (CSR):** 32-bit bus interface providing control flags, real-time telemetry readout registers, and dedicated fault-injection registers.
* **Safety-Critical FSM (*Zustandsautomat*):** 4-state engine supervisor (`IDLE`, `RUNNING`, `EMERGENCY`, `SHUTDOWN`) enforcing automated fuel cutoff upon overspeed ($N > 110\%$) or thermal runaway ($EGT > 1100^\circ\text{C}$).
* **Modern Co-Simulation Framework:** Verified with **Cocotb** using **Icarus Verilog (`iverilog`)** via standard IEEE VPI, eliminating vendor lock-in while maintaining synthesis readiness for **AMD/Xilinx Vivado**.

---

## Project Status & Roadmap

```text
[Phase 1] Floating-Point Golden Reference (Python)      --> [COMPLETED]
[Phase 2] Q16.16 Fixed-Point & SQNR Analysis (Python)   --> [COMPLETED]
[Phase 3] Hardware Architecture & Register Definition   --> [COMPLETED]
[Phase 4] Synthesizable Verilog Implementation (RTL)    --> [COMPLETED]
[Phase 5] Cocotb Co-Simulation & Bit-True Verification  --> [IN PROGRESS - ACTIVE]
[Phase 6] Boundary & Fault-Injection Verification       --> [UPCOMING]
[Phase 7] Portfolio Packaging & Synthesis Artifacts     --> [UPCOMING]
```

### 1. Completed Milestones

* **Phase 1: Mathematical Modeling & Floating-Point Reference (Python)**
  * Formulated continuous differential equations for spool inertia ($\tau_N = 1.5\text{ s}$), compressor volume lag ($\tau_P = 0.15\text{ s}$), and thermal combustion/cooling dynamics ($\tau_T = 0.8\text{ s}$).
  * Baseline continuous solver implemented in `aircraft_engine_simulator_floating.py`.
  * Defined normal flight profiles (Idle $\rightarrow$ Throttle Slam $\rightarrow$ Throttle Chop) and structural trip thresholds.

* **Phase 2: Fixed-Point Definition & Bit-True Simulation (Python)**
  * Selected two's-complement $Q16.16$ format (16-bit integer, 16-bit fractional).
  * Built bit-true integer model handling manual truncations and arithmetic shifts in `aircraft_engine_simulator_fixed_point.py`.
  * Quantization and saturation helper library implemented in `quantize_floats.py`.
  * Conducted SQNR analysis in `verify_software.py` guaranteeing numeric stability:
    * **Rotational Speed ($N$):** $\text{SQNR} = 57.90\text{ dB}$ (MAE: $0.22\%$)
    * **Compressor Pressure ($P$):** $\text{SQNR} = 60.97\text{ dB}$ (MAE: $0.41\text{ kPa}$)
    * **Exhaust Gas Temperature ($T$):** $\text{SQNR} = 65.29\text{ dB}$ (MAE: $1.05^\circ\text{C}$)
  * Interactive dual-mode visualizer with toggleable inspection curves implemented in `graph_visualizer.py`.
  * Exported golden reference dataset to `software_results.csv`.

* **Phase 3: Hardware Architecture & Register Design**
  * Specified pipelined hardware datapath with delay balancing across multiplier stages.
  * Designed memory-mapped 32-bit register map with 4-byte aligned offsets (`0x00` to `0x18`).
  * Designed two's-complement positive and negative saturation clamp logic.

* **Phase 4: Synthesizable Verilog Implementation (RTL)**
  * `clock_prescaler.v`: Parameterized clock divider generating the $1\text{ ms}$ simulation enable pulse (`clk_en_1ms`).
  * `calculate_target_values.v`: Pipelined calculation of $N_{\text{target}}$, $P_{\text{target}}$ (including $N^2$ squaring stage), and $T_{\text{target}}$.
  * `calculate_derivatives.v`: Pipelined rate calculation utilizing pre-calculated inverse time constants.
  * `calculate_next_steps.v`: First-order forward Euler integration accumulator with overflow protection and physical safeguard clamping.
  * `register_interface.v`: Memory-mapped bus controller handling control flags, telemetry readouts, and fault injection triggers.
  * `aircraft_engine_simulator_top.v`: Unified top-level entity integrating math blocks, register interface, and supervisory safety FSM.

* **Phase 5: Co-Simulation & Verification (Current Progress)**
  * Configured isolated Python virtual environment (`.venv`) and requirements manifest (`requirements.txt`).
  * Configured Cocotb runner targeting **Icarus Verilog (`iverilog`)** via open IEEE standard VPI.
  * Implemented object-oriented testbench harness (`EngineTester`) in `test_engine.py` encapsulating bus drivers (`bus_write`, `bus_read`), reset sequencers, and telemetry parsers.
  * Successfully verified initial RTL smoke test (`test_engine_smoke` passed with 0 test failures).

---

### 2. Current & Upcoming Work

* **Phase 5: Golden Reference Comparison (Active)**
  * [ ] Feed the full $20\text{-second}$ transient fuel cycle from `software_results.csv` through the register bus into hardware.
  * [ ] Assert bit-for-bit equality between RTL telemetry outputs and the Python fixed-point model.
* **Phase 6: Boundary, Limit, & Failure Injection Testing**
  * [ ] **Thermal Runaway Injection:** Command sustained over-fueling to verify hardware temperature trip and emergency FSM shutdown.
  * [ ] **Virtual Compressor Stall:** Assert Bit 0 of register `0x18` (`ADDR_FAULT_INJECTION`) to cut engine cooling airflow ($K_{\text{cool}} = 0$) and verify system collapse.
  * [ ] Log hardware failure traces and plot comparison against normal flight envelope using Matplotlib.
* **Phase 7: Portfolio Packaging & Vivado Synthesis**
  * [ ] Run Vivado synthesis and implementation report (LUT/FF/DSP resource utilization and $F_{\text{max}}$ timing closure).
  * [ ] Export VCD waveform dumps and capture timing diagrams.

---

## Memory-Mapped Register Map

The simulator exposes a standard 32-bit bus interface:

| Offset | Register Name | Access | Description / Bit Assignment |
| :---: | :--- | :---: | :--- |
| **`0x00`** | `ADDR_CONTROL` | R/W | **Bit 0:** `start_engine`<br>**Bit 1:** `restart_engine` |
| **`0x04`** | `ADDR_STATUS` | RO | **Bit 0:** `is_engine_broken` (1 = Emergency trip active) |
| **`0x08`** | `ADDR_FUEL_FLOW_COMMAND` | R/W | Commanded fuel flow rate ($W_f$) in $Q16.16$ [$\text{kg/h}$] |
| **`0x0C`** | `ADDR_SPEED` | RO | Current rotational speed ($N$) in $Q16.16$ [$\%$] |
| **`0x10`** | `ADDR_PRESSURE` | RO | Current compressor pressure ($P$) in $Q16.16$ [$\text{kPa}$] |
| **`0x14`** | `ADDR_TEMPERATURE` | RO | Current exhaust gas temperature ($T$) in $Q16.16$ [$^\circ\text{C}$] |
| **`0x18`** | `ADDR_FAULT_INJECTION` | R/W | **Bit 0:** `fault_compressor_stall` ($K_{\text{cool}} \rightarrow 0$)<br>**Bit 1:** `fault_sensor_corruption` |

---

## Repository Structure

```directory
├── model/
│   ├── aircraft_engine_simulator_floating.py     # Continuous floating-point reference model
│   ├── aircraft_engine_simulator_fixed_point.py  # Bit-true Q16.16 fixed-point model
│   ├── quantize_floats.py                        # Fixed-point quantization & saturation utilities
│   ├── verify_software.py                        # SQNR, MAE, MSE, and RMSE metric evaluation
│   └── graph_visualizer.py                       # Matplotlib dual-mode inspection UI
├── rtl/
│   ├── clock_prescaler.v                         # Parameterized simulation/hardware clock divider
│   ├── calculate_target_values.v                 # Pipelined target state evaluator
│   ├── calculate_derivatives.v                   # Division-free derivative stage
│   ├── calculate_next_steps.v                    # Euler integrator with saturation protection
│   ├── register_interface.v                      # Memory-mapped bus interface (CSR)
│   └── aircraft_engine_simulator_top.v           # Top-level entity with 4-state supervisory FSM
├── tb_cocotb/
│   └── test_engine.py                            # Object-oriented Cocotb verification harness
├── requirements.txt                              # Python environment dependencies
├── main.py                                       # Top-level execution & simulation runner script
└── README.md
```

---

## Quickstart & Simulation Execution

### 1. Prerequisites
* **Python 3.10+** (Official desktop release from [python.org](https://www.python.org/downloads/))
* **Icarus Verilog (`iverilog`)** (Install via `winget install -e --id Icarus.Verilog` on Windows)

### 2. Environment Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt
```

### 3. Run Verification Pipeline
```powershell
python main.py
```
This script executes:
1. Continuous-time floating-point reference simulation.
2. Bit-true $Q16.16$ integer model calculation.
3. Automated SQNR quantization noise analysis.
4. Icarus Verilog compilation and Cocotb hardware co-simulation with automated pass/fail assertion tables.
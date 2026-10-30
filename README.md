# Real-Time Jet Engine Simulator on FPGA (Hardware-in-the-Loop Emulation)

![CI Status](https://github.com/SarpArslan77/Aircraft-Engine-Simulation/actions/workflows/ci.yml/badge.svg)
![CI Status](https://github.com/SarpArslan77/Aircraft-Engine-Simulation/actions/workflows/ruff.yml/badge.svg)
![CI Status](https://github.com/SarpArslan77/Aircraft-Engine-Simulation/actions/workflows/verible.yml/badge.svg)

This project implements a synthesizable, real-time mathematical model of a single-spool turbojet engine designed for **Hardware-in-the-Loop (HIL) emulation** (*Echtzeitsimulation*) on an FPGA. By solving thermodynamic and mechanical differential equations directly in hardware at discrete time steps ($dt = 1\text{ ms}$), the simulator acts as an exact digital twin to verify Engine Control Units (ECUs) without physical engine test cells.

The engine dynamics track key physical states—**Rotational Speed ($N$)**, **Compressor Outlet Pressure ($P$)**, and **Exhaust Gas Temperature ($EGT$)**—driven by the control input **Fuel Flow ($W_f$)**.

---

## Key Engineering Highlights

* **Physics-Based Dynamics:** Solves continuous-time engine non-linear differential equations using first-order forward Euler integration ($dt = 1\text{ ms}$).
* **Fixed-Point Arithmetic (*Festkomma-Arithmetik*):** Custom $Q16.16$ bit-true implementation with zero hardware dividers; division operations are replaced with pre-scaled fractional constants to conserve DSP slices and maximize clock frequencies.
* **Deterministic Safety Clamping:** Custom hardware saturation logic prevents binary wrap-around overflow and enforces physical engine lower bounds ($N \ge 0$, $P \ge P_{\text{amb}}$, $T \ge T_{\text{amb}}$).
* **Memory-Mapped Register Map (CSR):** 32-bit AXI4-Lite bus interface providing control flags, real-time telemetry readout registers, and dedicated fault-injection registers.
* **Safety-Critical FSM (*Zustandsautomat*):** 4-state engine supervisor (`IDLE`, `RUNNING`, `EMERGENCY`, `SHUTDOWN`) enforcing automated fuel cutoff upon overspeed ($N > 110\%$) or thermal runaway ($EGT > 1100^\circ\text{C}$).
* **Automated Verification Pipeline:** End-to-end Python pipeline running Floating-Point reference -> Fixed-Point quantization -> Hardware Co-Simulation (Cocotb/Icarus Verilog) -> Automated Vivado Synthesis sweeping.

---

## Verification & Workflow Automation

The project features a highly automated execution script (`main.py`) which manages the full verification and synthesis lifecycle:

1. **Software Golden Reference:** Evaluates the continuous differential equations, followed by the integer-based bit-true fixed-point model. It calculates SQNR (Signal-to-Quantization-Noise Ratio) to guarantee numeric stability, logging results to `software_results.csv`.
2. **Hardware Co-Simulation (Cocotb):** The testbench (`tb/test_engine.py`) initializes the RTL via AXI4-Lite, feeds the time-series fuel flow commands from the software reference, and asserts cycle-accurate, bit-for-bit equality between the hardware telemetry outputs and the Python fixed-point model. It also features fault-injection testing (e.g., compressor stall triggers).
3. **Automated Synthesis Sweeping (`--synth`):** A custom Python wrapper (`scripts/run_synthesis.py`) drives AMD/Xilinx Vivado in batch mode via Tcl, performing binary searches to automatically find the maximum achievable clock frequency ($F_{\text{max}}$) and updating this README with the results.
4. **Linting (`--lint`):** Enforces strict code quality using Ruff for Python and Verible for SystemVerilog/Verilog.

---

## Memory-Mapped Register Map

The simulator exposes a standard 32-bit AXI4-Lite bus interface:

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

## FPGA Implementation & Synthesis Benchmarks

<!-- SYNTH_TABLE_START -->
| Metric / Hardware Resource | Used | Available (xc7a35tcpg236-1) | Utilization [%] |
| :--- | :--- | :--- | :--- |
| **Slice LUTs (Logic)** | 132 | 20,800 | 0.63 % |
| **Slice Registers (Flip-Flops)** | 186 | 41,600 | 0.45 % |
| **DSP48E1 Slices** | 0 | 90 | 0.00 % |
| **Target Clock ($F_{\text{target}}$)** | 307.69 MHz (3.25 ns) | - | - |
| **Achieved Clock ($F_{\text{max}}$)** | **309.89 MHz** | - | - |
| **Worst Negative Slack (WNS)** | **+0.023 ns** | - | **Timing Met** |

*Raw Vivado implementation reports: [`build_synth/utilization.rpt`](build_synth/utilization.rpt) and [`build_synth/timing.rpt`](build_synth/timing.rpt).*
<!-- SYNTH_TABLE_END -->

---

## Repository Structure

```directory
├── .github/workflows/            # CI/CD pipelines (Cocotb tests, Ruff, Verible)
├── build_synth/                  # Generated Vivado synthesis and timing reports
├── rtl/                          # Synthesizable Verilog HDL implementation
│   ├── aircraft_engine_simulator_top.v   # Top-level entity with 4-state supervisory FSM
│   ├── axi4_lite.v                       # Memory-mapped bus interface (CSR)
│   ├── calculate_target_values.v         # Pipelined target state evaluator
│   ├── calculate_derivatives.v           # Division-free derivative stage
│   ├── calculate_next_steps.v            # Euler integrator with saturation protection
│   └── clock_prescaler.v                 # Parameterized hardware clock divider
├── scripts/                      # Automation & toolchain scripts
│   ├── locate_iverilog_executable.py
│   ├── run_synthesis.py                  # Python wrapper for automated timing sweeps
│   └── synth.tcl                         # Vivado Out-of-Context (OOC) batch script
├── sim_model/                    # Python reference models & visualization
│   ├── aircraft_engine_simulator_floating.py     # Continuous floating-point reference model
│   ├── aircraft_engine_simulator_fixed_point.py  # Bit-true Q16.16 fixed-point model
│   ├── graph_visualizer.py                       # Matplotlib dual-mode inspection UI
│   ├── quantize_floats.py                        # Fixed-point quantization & saturation utilities
│   └── verify_software.py                        # SQNR, MAE, MSE, and RMSE metric evaluation
├── tb/                           # Cocotb hardware-in-the-loop testbench
│   └── test_engine.py                    # AXI bus drivers, telemetry parsers, and assertions
├── main.py                       # Top-level execution & simulation runner script
└── README.md

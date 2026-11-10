# Real-Time Jet Engine Simulator on FPGA (Hardware-in-the-Loop Emulation)

![CI Status](https://github.com/SarpArslan77/Aircraft-Engine-Simulation/actions/workflows/ci.yml/badge.svg)
![Ruff Status](https://github.com/SarpArslan77/Aircraft-Engine-Simulation/actions/workflows/ruff.yml/badge.svg)
![Verible Status](https://github.com/SarpArslan77/Aircraft-Engine-Simulation/actions/workflows/verible.yml/badge.svg)
![Verilator Status](https://github.com/SarpArslan77/Aircraft-Engine-Simulation/actions/workflows/verilator.yml/badge.svg)
![Mypy Status](https://github.com/SarpArslan77/Aircraft-Engine-Simulation/actions/workflows/mypy.yml/badge.svg)

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

## Mathematical Formulation & Engine Dynamics

The digital twin models the non-linear thermodynamic and mechanical transient dynamics of a single-spool turbojet engine. The system state is defined by three continuous state variables driven by the commanded fuel flow rate:

$$\mathbf{x}(t) = \begin{bmatrix} N(t) \\ P(t) \\ T(t) \end{bmatrix} \in \mathbb{R}^3, \quad u(t) = W_f(t) \in \mathbb{R}$$

* **$N(t)$:** Rotational Spool Speed [%]
* **$P(t)$:** Compressor Outlet Pressure [kPa]
* **$T(t)$:** Exhaust Gas Temperature (EGT) [°C]
* **$W_f(t)$:** Commanded Fuel Flow Rate [kg/h]

---

### 1. Continuous-Time Thermodynamic Differential Equations

The physical state transitions are governed by first-order non-linear differential equations capturing mechanical inertia, fluid volumetric lag, and thermal dissipation:

#### A. Rotational Speed Dynamics (Rotor Mechanical Inertia)
Rotor spool acceleration is constrained by turbine inertia $\tau_N$:

$$\tau_N \frac{dN(t)}{dt} + N(t) = N_{\text{target}}(t) = K_N \cdot W_f(t)$$

$$\frac{dN(t)}{dt} = \frac{1}{\tau_N} \left( K_N \cdot W_f(t) - N(t) \right)$$

#### B. Compressor Pressure Dynamics (Pneumatic Volume Lag)
Pressure buildup depends non-linearly on the square of rotational spool speed:

$$\tau_P \frac{dP(t)}{dt} + P(t) = P_{\text{target}}(t) = P_{\text{amb}} + K_P \cdot N(t)^2$$

$$\frac{dP(t)}{dt} = \frac{1}{\tau_P} \left( P_{\text{target}}(t) - P(t) \right)$$

#### C. Exhaust Gas Temperature Dynamics (Combustion Heat & Airflow Cooling)
Exhaust temperature rises proportionally to fuel combustion and cools via compressor mass-airflow:

$$\tau_T \frac{dT(t)}{dt} + T(t) = T_{\text{target}}(t) = T_{\text{amb}} + K_{\text{heat}} \cdot W_f(t) - K_{\text{cool}} \cdot N(t)$$

$$\frac{dT(t)}{dt} = \frac{1}{\tau_T} \left( T_{\text{target}}(t) - T(t) \right)$$

---

### 2. Division-Free Discrete Fixed-Point Transformation ($Q16.16$)

To eliminate multi-cycle latency hardware dividers on FPGA fabric, the differential equations are discretized using first-order forward Euler accumulation ($\Delta t = 1\text{ ms}$). The continuous time factors $(1 / \tau)$ are pre-computed and quantized into 16-bit fractional integration factors:

$$C = \text{round}\left( \frac{\Delta t}{\tau} \cdot 2^{16} \right)$$

The division-free discrete state derivatives evaluated at time step $k$ are:

$$dN[k] = \left( C_N \cdot \left( N_{\text{target}}[k] - N[k] \right) \right) \gg 16 \quad \text{with } C_N = \left\lfloor \frac{0.001}{1.5} \cdot 65536 \right\rceil = 44\text{ LSBs}$$

$$dP[k] = \left( C_P \cdot \left( P_{\text{target}}[k] - P[k] \right) \right) \gg 16 \quad \text{with } C_P = \left\lfloor \frac{0.001}{0.15} \cdot 65536 \right\rceil = 437\text{ LSBs}$$

$$dT[k] = \left( C_T \cdot \left( T_{\text{target}}[k] - T[k] \right) \right) \gg 16 \quad \text{with } C_T = \left\lfloor \frac{0.001}{0.8} \cdot 65536 \right\rceil = 82\text{ LSBs}$$

---

### 3. Physical Clamping & Safety Trip Thresholds

Hardware saturation logic bounds accumulated state values to prevent arithmetic two's-complement overflow and maintain true physical bounds:

* **Non-Negative Rotational Speed:**
  $$N[k+1] = \max(0, N[k] + dN[k])$$

* **Atmospheric Pressure Lower Bound:**
  $$P[k+1] = \max(P_{\text{amb}}, P[k] + dP[k])$$

* **Ambient Temperature Lower Bound:**
  $$T[k+1] = \max(T_{\text{amb}}, T[k] + dT[k])$$

* **Emergency Cutoff Trip Condition:**
  $$\text{Safety Trip} = (N[k] > 110\text{%}) \;\lor\; (T[k] > 1100^\circ\text{C})$$

---

### 4. Physical Parameter Reference Matrix

| Parameter / Coefficient | Symbol | Continuous Value | Engineering Unit | Quantized $Q16.16$ Representation |
| :--- | :---: | :---: | :---: | :---: |
| **Simulation Discrete Time-Step** | $\Delta t$ | $0.001$ | s | - |
| **Ambient Air Pressure** | $P_{\text{amb}}$ | $101.3$ | kPa | `6,638,797` LSBs |
| **Ambient Air Temperature** | $T_{\text{amb}}$ | $15.0$ | °C | `983,040` LSBs |
| **Spool Mechanical Inertia** | $\tau_N$ | $1.5$ | s | $C_N = 44$ LSBs |
| **Compressor Volume Lag** | $\tau_P$ | $0.15$ | s | $C_P = 437$ LSBs |
| **Thermal Mass Lag** | $\tau_T$ | $0.8$ | s | $C_T = 82$ LSBs |
| **Speed Gain Coefficient** | $K_N$ | $1.0$ | % / (kg/h) | `65,536` LSBs |
| **Pressure Gain Coefficient** | $K_P$ | $0.015$ | kPa / %² | `983` LSBs |
| **Combustion Heat Gain** | $K_{\text{heat}}$ | $15.0$ | °C / (kg/h) | `983,040` LSBs |
| **Mass-Airflow Cooling Gain** | $K_{\text{cool}}$ | $6.0$ | °C / % | `393,216` LSBs |
| **Maximum Safe Spool Speed** | $N_{\text{max}}$ | $110.0$ | % | `7,208,960` LSBs |
| **Maximum Safe EGT Temperature** | $T_{\text{max}}$ | $1100.0$ | °C | `72,089,600` LSBs |

---

## Quickstart & Build Targets

A root-level `Makefile` provides a unified, cross-platform entry point for developers and CI runners across Windows, Linux, and macOS:

| Command | Description | Wrapped Pipeline Stage |
| :--- | :--- | :--- |
| <code>make&nbsp;help</code> | Display formatted target palette and parameter override syntax | Dynamic inline docstring parser |
| <code>make&nbsp;sim</code> | Run software reference models & Cocotb hardware co-simulation | `python main.py` |
| <code>make&nbsp;synth</code> | Run single Out-of-Context (OOC) Vivado synthesis & STA | `python main.py --synth` |
| <code>make&nbsp;sweep</code> | Execute binary search clock frequency sweep for $F_{\text{max}}$ | `python main.py --sweep` |
| <code>make&nbsp;lint</code> | Run static code analysis checks (Ruff & Verible) | `python main.py --lint` |
| <code>make&nbsp;clean</code> | Remove transient artifacts (`sim_build/`, `*.log`, `*.jou`, `results.xml`) | Cross-platform Python cleaner |

### Dynamic Parameter Overrides

Default clock period constraints and frequency sweep intervals can be overridden directly from the command line without modifying source files:

```bash
# Run synthesis with a custom target period constraint (e.g., 8.5 ns)
make synth TARGET_PERIOD=8.5

# Run a binary search frequency sweep across custom bounds [LOW, HIGH] in ns
make sweep SWEEP_LOW_PERIOD=1.5 SWEEP_HIGH_PERIOD=8.0
```
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
| **`0x08`** | `ADDR_FUEL_FLOW_COMMAND` | R/W | Commanded fuel flow rate ($W_f$) in `Q16.16` [kg/h] |
| **`0x0C`** | `ADDR_SPEED` | RO | Current rotational speed ($N$) in `Q16.16` [%] |
| **`0x10`** | `ADDR_PRESSURE` | RO | Current compressor pressure ($P$) in `Q16.16` [kPa] |
| **`0x14`** | `ADDR_TEMPERATURE` | RO | Current exhaust gas temperature ($T$) in `Q16.16` [°C] |
| **`0x18`** | `ADDR_FAULT_INJECTION` | R/W | **Bit 0:** `fault_compressor_stall` ($K_{\text{cool}} \rightarrow 0$)<br>**Bit 1:** `fault_sensor_corruption` |

---

## FPGA Implementation & Synthesis Benchmarks

<!-- SYNTH_TABLE_START -->
| Metric / Hardware Resource | Used | Available (xc7a35tcpg236-1) | Utilization [%] |
| :--- | :--- | :--- | :--- |
| **Slice LUTs (Logic)** | 1,175 | 20,800 | 5.65 % |
| **Slice Registers (Flip-Flops)** | 643 | 41,600 | 1.55 % |
| **DSP48E1 Slices** | 4 | 90 | 4.44 % |
| **Target Clock ($F_{	ext{target}}$)** | 90.91 MHz<br>(11.00&nbsp;ns) | - | - |
| **Achieved Clock ($F_{	ext{max}}$)** | **91.09 MHz** | - | - |
| **Worst Negative Slack (WNS)** | **+0.022 ns** | - | **Timing Met** |

*Raw Vivado implementation reports: [`build_synth/utilization.rpt`](build_synth/utilization.rpt) and [`build_synth/timing.rpt`](build_synth/timing.rpt).*
<!-- SYNTH_TABLE_END -->

---

## Repository Structure

```directory
├── .github/workflows/                            # CI/CD pipelines (Cocotb tests, Ruff, Verible)
├── build_synth/                                  # Generated Vivado synthesis and timing reports
├── rtl/                                          # Synthesizable Verilog HDL implementation
│   ├── aircraft_engine_simulator_top.v           # Top-level entity with 4-state supervisory FSM
│   ├── axi4_lite.v                               # Memory-mapped bus interface (CSR)
│   ├── calculate_target_values.v                 # Pipelined target state evaluator
│   ├── calculate_derivatives.v                   # Division-free derivative stage
│   ├── calculate_next_steps.v                    # Euler integrator with saturation protection
│   └── clock_prescaler.v                         # Parameterized hardware clock divider
├── scripts/                                      # Automation & toolchain scripts
│   ├── locate_iverilog_executable.py
│   ├── run_synthesis.py                          # Python wrapper for automated timing sweeps
│   └── synth.tcl                                 # Vivado Out-of-Context (OOC) batch script
├── sim_model/                                    # Python reference models & visualization
│   ├── aircraft_engine_simulator_floating.py     # Continuous floating-point reference model
│   ├── aircraft_engine_simulator_fixed_point.py  # Bit-true Q16.16 fixed-point model
│   ├── graph_visualizer.py                       # Matplotlib dual-mode inspection UI
│   ├── quantize_floats.py                        # Fixed-point quantization & saturation utilities
│   └── verify_software.py                        # SQNR, MAE, MSE, and RMSE metric evaluation
├── tb/                                           # Cocotb hardware-in-the-loop testbench
│   └── test_engine.py                            # AXI bus drivers, telemetry parsers, and assertions
├── main.py                                       # Top-level execution & simulation runner script
└── README.md
```
---

## References & Literature

The mathematical modeling, calibration constants, and benchmark datasets implemented in this digital twin are grounded in the following experimental SR-30 micro-turbojet literature:

1. **M. P. Torres, G. Sosa, L. A. Amezquita-Brooks, E. Liceaga-Castro, and P. del C. Zambrano-Robledo**, *"Identification of the Fuel-Thrust Dynamics of a Gas Turbo Engine,"* in *52nd IEEE Conference on Decision and Control (CDC)*, Florence, Italy, Dec. 2013, pp. 4535–4540.  
   *(Provides the dynamic transfer function identification, physical engine limits at 87,000 RPM, and justification for the dominant rotor mechanical time constant $\tau \approx 0.75\text{--}1.5\text{ s}$.)*

2. **S. Bhartu**, *"MAS4 – Gas Turbine,"* Laboratory Report, School of Mechanical, Industrial & Aeronautical Engineering, University of the Witwatersrand, Johannesburg, Oct. 2017.  
   *(Provides the empirical calibration dataset: 15 steady-state operating points across 40,000 to 80,000 RPM recording fuel mass flow, compressor exit pressure ratio up to 2.82, and exhaust gas temperature).*

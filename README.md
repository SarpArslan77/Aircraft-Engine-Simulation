# Real-Time Jet Engine Simulator on FPGA (Hardware-in-the-Loop Emulation)

This project implements a real-time mathematical model of a single-spool turbojet engine designed for Hardware-in-the-Loop (HIL) emulation on an FPGA. By modeling thermodynamic and mechanical state changes in real time, the system provides a platform for verifying engine control units (ECUs) without requiring physical hardware.

The simulation tracks key engine states—**Rotational Speed ($N$)**, **Compressor Outlet Pressure ($P$)**, and **Exhaust Gas Temperature ($EGT$)**—driven by the control input **Fuel Flow ($W_f$)**.

---

## Project Status & Roadmap

To track development, the project is structured across several phases. Below is the current status of the implementation.

### 1. Already Done Part
*   **Phase 1: Mathematical Modeling & Floating-Point Reference (Python)**
    *   Developed the continuous-time physics equations using Euler's integration ($dt = 1\text{ ms}$).
    *   Implemented the baseline model in `aircraft_engine_simulator_floating.py`.
    *   Defined operational limits and thermal runaway/overspeed thresholds.
*   **Phase 2: Fixed-Point Definition & Bit-True Simulation (Python)**
    *   Designed a $Q16.16$ fixed-point format scheme to prepare for hardware implementation.
    *   Implemented the bit-true integer model with manual bit-shifting and truncation handling in `aircraft_engine_simulator_fixed_point.py`.
    *   Created utility functions for float quantization and saturation in `quantize_floats.py`.
    *   Built an interactive visualization suite in `graph_visualizer.py` using Matplotlib to compare floating-point and fixed-point behaviors side-by-side.
*   **Phase 3: Hardware Architecture & Register Design**
    *   Designed the hardware datapath pipelines for the target calculation and integration stages.
*   **Phase 4: Synthesizable Verilog Implementation (In Progress)**
    *   Implemented `calculate_target_values.v` utilizing $32$-bit signed multipliers and right-shifting for $Q16.16$ compatibility.
    *   Implemented `calculate_next_step.v` containing the Euler integration step and boundary-clamping safety logic.

---

### 2. Working On (Current & Next Steps)
*   **Phase 4: Synthesizable Verilog Implementation (Completion)**
    *   [ ] **Writing `calculate_derivatives.v`**: Implementing the scaled time-constant division approximation logic to avoid hardware division blocks.
    *   [ ] **Writing `aircraft_engine_simulator_top.v`**: Connecting the target, derivative, and next-step modules together into a unified pipeline with control registers.
*   **Phase 5: Co-Simulation & Verification (Cocotb + Vivado)**
    *   [ ] Setting up the Cocotb testbench structure.
    *   [ ] Configuring Cocotb to interface with Xilinx Vivado's simulator (`xsim`).
    *   [ ] Implementing bit-true comparison tests checking the Verilog output against the Python fixed-point model.
*   **Phase 6: Boundary, Limit, & Failure Injection Testing**
    *   [ ] Implementing fault registers in Verilog to simulate turbine degradation and compressor stalls.
    *   [ ] Verifying hardware-level shutdown triggers when exceeding safety limits (e.g., $EGT > 950^\circ\text{C}$ or $N > 110\%$).

---

## Repository Structure

```directory
├── model/
│   ├── aircraft_engine_simulator_floating.py     # Continuous-time floating-point reference model
│   ├── aircraft_engine_simulator_fixed_point.py  # Bit-true Q16.16 fixed-point simulator
│   ├── quantize_floats.py                        # Quantization and saturation helpers
│   ├── graph_visualizer.py                       # Matplotlib-based UI for comparison & analysis
│   └── main.py                                   # Runs simulations and displays visual plots
└── rtl/
    ├── calculate_target_values.v                 # Target value calculation stage (Complete)
    ├── calculate_next_step.v                     # Euler integration and output clamping (Complete)
    ├── calculate_derivatives.v                   # [WIP] Intermediate rate calculations
    └── aircraft_engine_simulator_top.v           # [WIP] Top-level FPGA wrapper & registers
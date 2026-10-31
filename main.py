
#* main.py

#* ======= Libraries =======
# ------- Natives. -------
import json
import numpy as np
import os
import subprocess
import sys

from pathlib import Path
from typing import Any

# ------- Externals. -------
#? get_runner(): Factory function, returns a simulator-specific controller.
from cocotb_tools.runner import Runner, get_runner
from numpy import float64
from numpy.typing import NDArray

# ------- Customs. -------
from scripts.locate_iverilog_executable import locate_iverilog_executable
from scripts.run_synthesis import ConfigSynthesisRunner, SynthesisRunner
from sim_model.aircraft_engine_simulator_fixed_point import (
    AircraftEngineSimulatorFixedPoint,
    ConfigAircraftEngineSimulatorFixedPoint,
)
from sim_model.aircraft_engine_simulator_floating import (
    AircraftEngineSimulatorFloating,
    ConfigAircraftEngineSimulatorFloating,
)
from sim_model.graph_visualizer import ConfigGraphVisualizer, GraphVisualizer
from sim_model.quantize_floats import quantize_floats
from sim_model.verify_software import SoftwareVerifier
from subprocess import CompletedProcess

#* ======= Main Loop =======
if __name__ == "__main__":
    # ------- Configurations. -------
    # Locates Icarus Verilog and adds to the environment path.
    iverilog_executable_path: Path = locate_iverilog_executable(hardcoded_iverilog_path = "C:/iverilog/bin")
    iverilog_bin_dir: str = str(iverilog_executable_path.parent)

    #? "PATH": OSvariable containing list of folders, where
    #   executable programs live
    #? os.environ: Dictionary containing all current system environment variables.
    if iverilog_bin_dir not in os.environ.get("PATH", ""):
        #? os.pathsep: Gives back the correct seperator for the active OS.
        os.environ["PATH"] = iverilog_bin_dir + os.pathsep + os.environ.get("PATH", "")

    # ------- Constants. -------
    # Paths.
    MAIN_DIR_PATH = Path(__file__).resolve().parent

    SOFTWARE_RESULTS_FILE_NAME: str = "software_results"
    SOFTWARE_RESULTS_FILE_PATH: Path = MAIN_DIR_PATH / f"{SOFTWARE_RESULTS_FILE_NAME}.csv"

    RTL_DIR_PATH: Path = MAIN_DIR_PATH / "rtl"
    TB_DIR_PATH: Path = MAIN_DIR_PATH / "tb"
    BUILD_SYNTH_DIR_PATH: Path = MAIN_DIR_PATH / "build_synth"
    SCRIPTS_DIR_PATH: Path = MAIN_DIR_PATH / "scripts"
    TCL_SCRIPT_PATH: Path = SCRIPTS_DIR_PATH / "synth.tcl"
    README_FILE_PATH: Path = MAIN_DIR_PATH / "README.md"

    HARDCODED_VIVADO_PATH: Path = Path(r"D:\Programs\2025.2\Vivado\bin\vivado.bat")

    # Declares only the constants, which are used in multiple places,
    #   otherwise they are directly declared in the class initializtion.
    INT_BIT_WIDTH: int = 16
    FRACTIONAL_BIT_WIDTH: int = 16

    SIMULATION_STEP: float = 1e-3
    TOTAL_SIMULATION_TIME: float = 20.0 # [s].

    AMBIENT_PRESSURE: float = 101.3 # [kPa].
    AMBIENT_TEMPERATURE: float = 15.0

    ROTOR_INERTIAL_TIME_CONST: float = 1.5
    PRESSURE_VOLUME_TIME_CONST: float = 0.15
    THERMAL_TIME_CONST: float = 0.8

    SPEED_GAIN_COEFF: float = 1.0
    COMPRESSOR_PRESSURE_GAIN: float = 1.5e-2
    COMBUSTION_HEAT_GAIN: float = 15.0
    MASS_OVERFLOW_COOLING_GAIN: float = 6.0

    MAX_ROTATIONAL_SPEED: float = 110.0
    MAX_COMPRESSOR_TEMPERATURE: float = 1100.0

    # Quantized Values.
    AMBIENT_PRESSURE_QUANTIZED: int = quantize_floats(AMBIENT_PRESSURE, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)
    AMBIENT_TEMPERATURE_QUANTIZED: int = quantize_floats(AMBIENT_TEMPERATURE, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)

    PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST_QUANTIZED: int = quantize_floats((SIMULATION_STEP / ROTOR_INERTIAL_TIME_CONST), INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)
    PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST_QUANTIZED: int = quantize_floats((SIMULATION_STEP / PRESSURE_VOLUME_TIME_CONST), INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)
    PRE_CALCULATED_THERMAL_TIME_CONST_QUANTIZED: int = quantize_floats((SIMULATION_STEP / THERMAL_TIME_CONST), INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)

    SPEED_GAIN_COEFF_QUANTIZED: int = quantize_floats(SPEED_GAIN_COEFF, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)
    COMPRESSOR_PRESSURE_GAIN_QUANTIZED: int = quantize_floats(COMPRESSOR_PRESSURE_GAIN, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)
    COMBUSTION_HEAT_GAIN_QUANTIZED: int = quantize_floats(COMBUSTION_HEAT_GAIN, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)
    MASS_OVERFLOW_COOLING_GAIN_QUANTIZED: int = quantize_floats(MASS_OVERFLOW_COOLING_GAIN, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)

    MAX_ROTATIONAL_SPEED_QUANTIZED: int = quantize_floats(MAX_ROTATIONAL_SPEED, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)
    MAX_COMPRESSOR_TEMPERATURE_QUANTIZED: int = quantize_floats(MAX_COMPRESSOR_TEMPERATURE, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)

    # Hardware Simulation.
    TOP_MODULE: str = "aircraft_engine_simulator_top"

    VERILOG_SRC_FILE_PATHS: list[Path] = [
        RTL_DIR_PATH / "clock_prescaler.v",
        RTL_DIR_PATH / "calculate_target_values.v",
        RTL_DIR_PATH / "calculate_derivatives.v",
        RTL_DIR_PATH / "calculate_next_steps.v",
        RTL_DIR_PATH / "axi4_lite.v",
        RTL_DIR_PATH / f"{TOP_MODULE}.v"
    ]

    TARGET_PERIOD_NS: float = 10.000
    LOW_PERIOD_NS: float = 2.000
    HIGH_PERIOD_NS: float = 10.000

    # Exports a JSON File, which containts parameters for other files.
    config: dict[str, dict[str, Any]] = {
        "test_engine" : {
            "addr_control": 0x00,
            "addr_status": 0x04,
            "addr_fuel_flow_command": 0x08,
            "addr_speed": 0x0C,
            "addr_pressure": 0x10,
            "addr_temperature": 0x14,
            "addr_fault_injection": 0x18,

            "software_results_file_path_str": str(SOFTWARE_RESULTS_FILE_PATH),

            "simulation_step": SIMULATION_STEP,
            "total_simulation_time": TOTAL_SIMULATION_TIME,

            "fractional_bit_width": FRACTIONAL_BIT_WIDTH,

            "max_compressor_temperature": MAX_COMPRESSOR_TEMPERATURE,

            "smoke_test_duration": 5e-2,
            "compressor_stall_test_duration": 5e-1,
            "max_thermal_threshold_cross_duration": 3
        }
    }

    with open( 
        file = f"{TB_DIR_PATH}/config.json",
        mode = "w",
        encoding = "utf-8"
    ) as f:
        json.dump(
            config, 
            f, 
            indent = 4
        )

    # ------- User-Specifiec Inputs. -------
    SHOULD_FIND_MAX_FREQ: bool = True

    # ------- Custom Classes. -------
    # Aircraft Engine (Floating Type).
    config_aircraft_engine_simulator_floating = ConfigAircraftEngineSimulatorFloating(
        simulation_step = SIMULATION_STEP,
        total_simulation_time = TOTAL_SIMULATION_TIME,

        ambient_pressure = AMBIENT_PRESSURE,
        ambient_temperature = AMBIENT_TEMPERATURE,

        rotor_inertial_time_const = ROTOR_INERTIAL_TIME_CONST,
        pressure_volume_time_const = PRESSURE_VOLUME_TIME_CONST,
        thermal_time_const = THERMAL_TIME_CONST,

        speed_gain_coeff = SPEED_GAIN_COEFF,
        compressor_pressure_gain = COMPRESSOR_PRESSURE_GAIN,
        combustion_heat_gain = COMBUSTION_HEAT_GAIN,
        mass_overflow_cooling_gain = MASS_OVERFLOW_COOLING_GAIN,

        max_rotational_speed = MAX_ROTATIONAL_SPEED,
        max_compressor_temperature = MAX_COMPRESSOR_TEMPERATURE
    )

    aircraft_engine_simulator_floating = AircraftEngineSimulatorFloating(
        config_aircraft_engine_simulator_floating = config_aircraft_engine_simulator_floating
    )

    # Aircraft Engine (Fixed Point Type).
    #   Quantizes all the attributes from the floating type to the fixed point type.
    config_aircraft_engine_simulator_fixed_point = ConfigAircraftEngineSimulatorFixedPoint(
        int_bit_width = INT_BIT_WIDTH,
        fractional_bit_width = FRACTIONAL_BIT_WIDTH,

        simulation_step = SIMULATION_STEP,
        total_simulation_time = TOTAL_SIMULATION_TIME,
    
        ambient_pressure_quantized = AMBIENT_PRESSURE_QUANTIZED,
        ambient_temperature_quantized = AMBIENT_TEMPERATURE_QUANTIZED,
    
        pre_calculated_rotor_inertial_time_const_quantized = PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST_QUANTIZED,
        pre_calculated_pressure_volume_time_const_quantized = PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST_QUANTIZED,
        pre_calculated_thermal_time_const_quantized = PRE_CALCULATED_THERMAL_TIME_CONST_QUANTIZED,
    
        speed_gain_coeff_quantized = SPEED_GAIN_COEFF_QUANTIZED,
        compressor_pressure_gain_quantized = COMPRESSOR_PRESSURE_GAIN_QUANTIZED,
        combustion_heat_gain_quantized = COMBUSTION_HEAT_GAIN_QUANTIZED,
        mass_overflow_cooling_gain_quantized = MASS_OVERFLOW_COOLING_GAIN_QUANTIZED,
    
        max_rotational_speed_quantized = MAX_ROTATIONAL_SPEED_QUANTIZED,
        max_compressor_temperature_quantized = MAX_COMPRESSOR_TEMPERATURE_QUANTIZED,

        software_results_file_path = SOFTWARE_RESULTS_FILE_PATH
    )
    
    aircraft_engine_simulator_fixed_point = AircraftEngineSimulatorFixedPoint(
        config_aircraft_engine_simulator_fixed_point = config_aircraft_engine_simulator_fixed_point
    )

    # Software Verification.
    software_verifier = SoftwareVerifier()

    # Graph.
    config_graph_visualizer = ConfigGraphVisualizer(
        # ------- Plot Attributes. -------
        # Fuel Flow and Speed (Floating).
        fuel_flow_floating_linestyle = "--",
        fuel_flow_floating_color = "gray",
        fuel_flow_floating_linewidth = 1.5,

        # Fuel Flow (Fixed Point).
        fuel_flow_fixed_point_linestyle = ":",
        fuel_flow_fixed_point_color = "black",
        fuel_flow_fixed_point_linewidth = 1.5,

        # Speed (Floating).
        speed_floating_linestyle = "-",
        speed_floating_color = "blue",
        speed_floating_linewidth = 2.0,

        # Speed (Fixed Point).
        speed_fixed_point_linestyle = "-.",
        speed_fixed_point_color = "darkblue",
        speed_fixed_point_linewidth = 2.0,

        # Fuel Flow & Speed Grid.
        fuel_flow_and_speed_grid_linestyle = ":",
        fuel_flow_and_speed_grid_alpha = 0.6,

        # Pressure (Floating).
        pressure_floating_linestyle = "-",
        pressure_floating_color = "purple",
        pressure_floating_linewidth = 2.0,

        # Pressure (Fixed Point).
        pressure_fixed_point_linestyle = "-.",
        pressure_fixed_point_color = "indigo",
        pressure_fixed_point_linewidth = 2.0,

        # Pressure Grid.
        pressure_grid_linestyle = ":",
        pressure_grid_alpha = 0.6,

        # Temperature (Floating).
        temperature_floating_linestyle = "-",
        temperature_floating_color = "red",
        temperature_floating_linewidth = 2.0,

        # Temperature (Fixed Point).
        temperature_fixed_point_linestyle = "-.",
        temperature_fixed_point_color = "darkred",
        temperature_fixed_point_linewidth = 2.0,

        # Temperature Grid.
        temperature_grid_linestyle = ":",
        temperature_grid_alpha = 0.6,

        # ------- Marker Conditions. -------
        max_speed = MAX_ROTATIONAL_SPEED,

        engine_failure_line_color = "darkred",
        engine_failure_line_linestyle = ":",
        engine_failure_line_linewidth = 1.5,

        engine_failure_text_color = "darkred",
        engine_failure_text_fontsize = 9,
        engine_failure_text_fontweight = "bold"
    )

    graph_visualizer = GraphVisualizer(
        config_graph_visualizer = config_graph_visualizer
    )

    # Synthesis.
    config_synthesis_runner = ConfigSynthesisRunner(
        main_dir_path = MAIN_DIR_PATH,
        build_synth_dir_path = BUILD_SYNTH_DIR_PATH,
        scripts_dir_path = SCRIPTS_DIR_PATH,
        tcl_script_path = TCL_SCRIPT_PATH,
        readme_file_path = README_FILE_PATH,

        hardcoded_vivado_path = HARDCODED_VIVADO_PATH
    )

    synthesis_runner = SynthesisRunner(config_synthesis_runner = config_synthesis_runner)

    # ------- Workflow. -------
    # Runs the aircraft engine simulation both floating and fixed point.
    fuel_flow_history_floating, speed_history_floating, pressure_history_floating, temperature_history_floating, time_history = aircraft_engine_simulator_floating.run_simulation(
        initial_conditions = (0.0, AMBIENT_PRESSURE, AMBIENT_TEMPERATURE)
    )

    #: time_history stays stable independent from the representation, so it doesnt need to be returned from floating simulation as well.
    fuel_flow_history_fixed_point, speed_history_fixed_point, pressure_history_fixed_point, temperature_history_fixed_point, is_engine_broken_history, _ = aircraft_engine_simulator_fixed_point.run_simulation(
        initial_conditions = (
            0, 
            quantize_floats(AMBIENT_PRESSURE, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True), 
            quantize_floats(AMBIENT_TEMPERATURE, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True)
        )
    )

    # Scales the integer values from fixed point representation back to the normal range.
    fixed_point_scale_factor: int = 2 ** FRACTIONAL_BIT_WIDTH
    
    fuel_flow_history_fixed_point_scaled: NDArray[float64] = fuel_flow_history_fixed_point / fixed_point_scale_factor
    speed_history_fixed_point_scaled: NDArray[float64] = speed_history_fixed_point / fixed_point_scale_factor
    pressure_history_fixed_point_scaled: NDArray[float64] = pressure_history_fixed_point / fixed_point_scale_factor
    temperature_history_fixed_point_scaled: NDArray[float64] = temperature_history_fixed_point / fixed_point_scale_factor

    # Compares the accuracy of fixed-point against floating-point.
    print()
    print("Quantization Verification Results: ")

    # Calculates the error between the floating and fixed-point.
    fuel_flow_error: NDArray = fuel_flow_history_floating - fuel_flow_history_fixed_point_scaled
    speed_error: NDArray = speed_history_floating - speed_history_fixed_point_scaled
    pressure_error: NDArray = pressure_history_floating - pressure_history_fixed_point_scaled
    temperature_error: NDArray = temperature_history_floating - temperature_history_fixed_point_scaled

    software_verifier.run_software_verifier(
        original_signal = fuel_flow_history_floating,
        error = fuel_flow_error,
        state_name = "Fuel Flow"
    )

    software_verifier.run_software_verifier(
        original_signal = speed_history_floating,
        error = speed_error,
        state_name = "Rotational Speed"
    )

    software_verifier.run_software_verifier(
        original_signal = pressure_history_floating,
        error = pressure_error,
        state_name = "Compressor Pressure"
    )

    software_verifier.run_software_verifier(
        original_signal = temperature_history_floating,
        error = temperature_error,
        state_name = "Exhaust Gas Temperature"
    )

    # Plots the data.
    graph_visualizer.run_visualization(
        histories_floating = (fuel_flow_history_floating, speed_history_floating, pressure_history_floating, temperature_history_floating),
        histories_fixed_point_scaled = (fuel_flow_history_fixed_point_scaled, speed_history_fixed_point_scaled, pressure_history_fixed_point_scaled, temperature_history_fixed_point_scaled),

        time_history = time_history,

        show_plots = False
    )

    # ------- Hardware Simulation. -------
    # Selects the iCarus Verilog runner.
    runner: Runner = get_runner("icarus")

    #? .build(): Translates Python configuration into exact command-line
    #   arguments required by target compiler.
    #   - sources: List of paths to the source files.
    #   - hdl_toplevel: Name of the top-level module.
    #   - parameters: Dictionary mapping hdl parameters.
    #   - always: True: Forces a complete recompile every time.
    #             False: Checks file timestamps and skips recompiling if source haven't changed.
    # Compiles the verilog files.
    runner.build(
        sources = VERILOG_SRC_FILE_PATHS,
        hdl_toplevel = TOP_MODULE,
        parameters = {
            "SYSTEM_CLK_FREQ": 25,
            "TARGET_CLK_FREQ": 1,

            "INTEGER_BIT_WIDTH": INT_BIT_WIDTH,
            "FRACTIONAL_BIT_WIDTH": FRACTIONAL_BIT_WIDTH,

            "AMBIENT_PRESSURE": AMBIENT_PRESSURE_QUANTIZED,
            "AMBIENT_TEMPERATURE": AMBIENT_TEMPERATURE_QUANTIZED,

            "SPEED_GAIN_COEFF": SPEED_GAIN_COEFF_QUANTIZED,
            "COMPRESSOR_PRESSURE_GAIN": COMPRESSOR_PRESSURE_GAIN_QUANTIZED,
            "COMBUSTION_HEAT_GAIN": COMBUSTION_HEAT_GAIN_QUANTIZED,
            "MASS_OVERFLOW_COOLING_GAIN": MASS_OVERFLOW_COOLING_GAIN_QUANTIZED,

            "PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST": PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST_QUANTIZED,
            "PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST": PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST_QUANTIZED,
            "PRE_CALCULATED_THERMAL_TIME_CONST": PRE_CALCULATED_THERMAL_TIME_CONST_QUANTIZED,

            "MAX_ROTATIONAL_SPEED": MAX_ROTATIONAL_SPEED_QUANTIZED,
            "MAX_COMPRESSOR_TEMPERATURE": MAX_COMPRESSOR_TEMPERATURE_QUANTIZED
        },
        always = True
    )

    # Runs the testbench.
    runner.test(
        hdl_toplevel = TOP_MODULE,
        test_module = "test_engine",
        test_dir = TB_DIR_PATH
    )

    # 'python main.py --synth'.
    if ("--synth" in sys.argv):
        # Sweeps for different frequencies until the maximum frequencies is reached.
        if SHOULD_FIND_MAX_FREQ:
            print()
            print(f"Calculating the maximum frequency by trying ones between [{LOW_PERIOD_NS}, {HIGH_PERIOD_NS}]...")
            
            adjusted_high_period_ns: float = HIGH_PERIOD_NS
            adjusted_low_period_ns: float = LOW_PERIOD_NS

            # Stores the lowest synthesizable period, defaults to the highest possible period.
            best_synthesizable_period: float  = HIGH_PERIOD_NS
            best_wns: float = -np.inf

            while ((adjusted_high_period_ns - adjusted_low_period_ns) > 0.100):
                # Calculates the test period.
                test_period_ns: float = round(((adjusted_high_period_ns + adjusted_low_period_ns) / 2), 3)
                
                wns: float = synthesis_runner.run_synthesis(
                    target_period_ns = test_period_ns,
                    should_update_readme = False
                )

                # Updates the period boundaries.
                if (wns >= 0.000):
                    adjusted_high_period_ns = test_period_ns

                    # Updates the best period and wns.
                    best_synthesizable_period = test_period_ns
                    best_wns = wns
                else:
                    adjusted_low_period_ns = test_period_ns

                print(f"-> Period: {test_period_ns} & WNS: {wns}")

            # Re-runs the synthesis with the highst frequency for updating the 'README' file.
            _ = synthesis_runner.run_synthesis(
                target_period_ns = best_synthesizable_period,
                should_update_readme = True
            )

            print()
            print(f" --> Best (Shortest) Period {best_synthesizable_period} | Best (Lowest) WNS: {best_wns}")

        # Runs the synthesis with the specified target frequency.
        else:
            _ = synthesis_runner.run_synthesis(
                target_period_ns = TARGET_PERIOD_NS,
                should_update_readme = True
            )

    # 'python main.py --lint'.
    if ("--lint" in sys.argv):
        # Runs Ruff.
        ruff_result: CompletedProcess = subprocess.run(
            ["ruff", "check", "."],
            cwd = MAIN_DIR_PATH    
        )

        # Runs Verible.
        verilog_file_paths: list[str] = [str(file_path) for file_path in VERILOG_SRC_FILE_PATHS]

        verible_result: CompletedProcess = subprocess.run(
            ["verible-verilog-lint", "--rules_config", ".rules.verible_lint"] + verilog_file_paths,
            cwd = MAIN_DIR_PATH
        )

        # Checks for failures.
        if (ruff_result.returncode != 0) or (verible_result.returncode != 0):
            print("Linting failed!")
            # Exits with an error code so Git knows it failed.
            sys.exit(1)
        else: 
            print("Linting passed!")

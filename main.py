
#* main.py

#* ======= Libraries =======
# ------- Natives. -------
import json
import numpy as np
import os
import shutil
import subprocess
import sys

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

# ------- Externals. -------
#? get_runner(): Factory function, returns a simulator-specific controller.
from cocotb_tools.runner import Runner, get_runner
from numpy import float64
from numpy.typing import NDArray

# ------- Customs. -------
from scripts.config_loader import ConfigLoader, SystemConfig
from scripts.generate_verilog_header_file import generate_verilog_header_file
from scripts.locate_executables import locate_iverilog_executable, locate_verilator_executable
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
from sim_model.verify_software import SoftwareVerifier
from subprocess import CompletedProcess

#* ======= Main Loop =======
if __name__ == "__main__":
    # ------- Configurations. -------
    # Locates Icarus Verilog and adds to system PATH if present.
    iverilog_executable_path: Path | None = None

    try:
        iverilog_executable_path = locate_iverilog_executable(hardcoded_iverilog_path = "C:/iverilog/bin")
        iverilog_bin_dir: str = str(iverilog_executable_path.parent)

        if iverilog_bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = iverilog_bin_dir + os.pathsep + os.environ.get("PATH", "")
    except FileNotFoundError:
        print("[NOTE] Icarus Verilog not found locally (hardware sim will be enforced in CI).")

    # Silences Python warning filter for Cocotb runner.
    os.environ["PYTHONWARNINGS"] = "ignore::DeprecationWarning"

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

    TOP_MODULE: str = "aircraft_engine_simulator_top"
    VERILOG_SRC_FILE_PATHS: list[Path] = [
        RTL_DIR_PATH / "clock_prescaler.v",
        RTL_DIR_PATH / "calculate_target_values.v",
        RTL_DIR_PATH / "calculate_derivatives.v",
        RTL_DIR_PATH / "calculate_next_steps.v",
        RTL_DIR_PATH / "axi4_lite.v",
        RTL_DIR_PATH / f"{TOP_MODULE}.v"
    ]

    CONFIG_FILE_PATH: Path = MAIN_DIR_PATH / "config.toml"

    # Creates a Central Single Source of Trurh (CSST).
    config_loader = ConfigLoader()
    cfg: SystemConfig = config_loader.load_config(config_file_path = CONFIG_FILE_PATH)


    # Exports a JSON File, which containts parameters for other files.
    config: dict[str, dict[str, Any]] = {
        "test_engine" : {
            "addr_control": cfg.register.addr_control,
            "addr_status": cfg.register.addr_status,
            "addr_fuel_flow_cmd": cfg.register.addr_fuel_flow_cmd,
            "addr_speed": cfg.register.addr_speed,
            "addr_pressure": cfg.register.addr_pressure,
            "addr_temperature": cfg.register.addr_temperature,
            "addr_fault_injection": cfg.register.addr_fault_injection,

            "software_results_file_path_str": str(SOFTWARE_RESULTS_FILE_PATH),

            "simulation_step": cfg.simulation.simulation_step,
            "total_simulation_time": cfg.simulation.total_simulation_time,

            "fractional_bit_width": cfg.representation.fractional_bit_width,

            "max_compressor_temperature": cfg.limit.max_compressor_temperature,

            "smoke_test_duration": cfg.testbench.smoke_test_duration,
            "compressor_stall_test_duration": cfg.testbench.compressor_stall_test_duration,
            "max_thermal_threshold_cross_duration": cfg.testbench.max_thermal_threshold_cross_duration
        }
    }

    target_config_path: Path = TB_DIR_PATH / "config.json"
    try:
        # Ensures the target directory exists.
        target_config_path.parent.mkdir(
            parents = True,
            exist_ok = True
        )

        with open(
            file = target_config_path,
            mode = "w",
            encoding = "utf-8"
        ) as f:
            json.dump(
                config,
                f,
                indent = 4
            )
    except TypeError as err:
        # Traps non-serializable objects.
        raise TypeError(
            f"Failed to serialize testbench configurations into JSON format: {err}"
        ) from err
    except OSError as err:
        # Traps disk full, read-only permissions or filesystem locks.
        raise RuntimeError(
            f"Failed to write testbench configuration to '{target_config_path}': {err}"
        ) from err

    # Defines the parameters.
    ENGINE_MATH_PARAMETERS = {
        "INT_BIT_WIDTH": cfg.representation.int_bit_width,
        "FRACTIONAL_BIT_WIDTH": cfg.representation.fractional_bit_width,

        "AMBIENT_PRESSURE": cfg.ambient.ambient_pressure_quantized,
        "AMBIENT_TEMPERATURE": cfg.ambient.ambient_temperature_quantized,

        "SPEED_GAIN_COEFF": cfg.gain.speed_gain_coeff_quantized,
        "COMPRESSOR_PRESSURE_GAIN": cfg.gain.compressor_pressure_gain_quantized,
        "COMBUSTION_HEAT_GAIN": cfg.gain.combustion_heat_gain_quantized,
        "MASS_OVERFLOW_COOLING_GAIN": cfg.gain.mass_overflow_cooling_gain_quantized,

        "PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST": cfg.inertia.pre_calculated_rotor_inertial_time_const_quantized,
        "PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST": cfg.inertia.pre_calculated_pressure_volume_time_const_quantized,
        "PRE_CALCULATED_THERMAL_TIME_CONST": cfg.inertia.pre_calculated_thermal_time_const_quantized,

        "MAX_ROTATIONAL_SPEED": cfg.limit.max_rotational_speed_quantized,
        "MAX_COMPRESSOR_TEMPERATURE": cfg.limit.max_compressor_temperature_quantized
    }

    COCOTB_PARAMETERS = {
        **ENGINE_MATH_PARAMETERS,
        "SYSTEM_CLK_FREQ": 25,
        "TARGET_CLK_FREQ": 1,
    }

    TOP_MODULE_PARAMETERS = {
        **ENGINE_MATH_PARAMETERS,
        "SYSTEM_CLK_FREQ": 100_000_000,
        "TARGET_CLK_FREQ": 1_000,
    }

    # Saves the hardware parameters as verilog header file, so it can be imported in top module.
    generate_verilog_header_file(
        file_name = "top_module_params.vh",
        parameters = TOP_MODULE_PARAMETERS,
        verilog_header_file_dir_path = RTL_DIR_PATH
    )

    # ------- Parsing. -------
    # Creates top-level parser.
    parser = ArgumentParser(description = "Aircraft Engine Simulation & Verification Pipeline.")
    
    # Mutually exclusive group: either a single synthesis run OR a frequency sweep, never both.
    synthesizer_group = parser.add_mutually_exclusive_group()
    
    #? nargs: Number of arguments:
    #   -> '?': 0 or 1 value.
    #   -> '*': 0 or more values.
    #? default = None: The value assigned to 'args.<name>' when the user does
    #       not type that flag at all in the terminal.
    #? help: Human-readable explanation string displayed when 'python main.py --help' / 'python main.py -h'.
    #? metavar: Meta-Variable, controls the visual placeholder name shown in the '--help' menu output.
    # Synthesizes with a target period (default 'TARGET_PERIOD': 3.250 ns).
    # -> 'python main.py --synth': Uses 'TARGET_PERIOD'.
    # -> 'python main.py --synth 4.000': Uses 4.000 ns.
    synthesizer_group.add_argument(
        "--synth",
        nargs = "?",
        const = cfg.synthesis.synth_target_period,
        type = float,
        default = None,
        help = f"Run single Out-of-Context synthesis. Optional target period in [ns] (default: {cfg.synthesis.synth_target_period})."
    )
    
    # Sweeps target periods in an interval to discover maximum frequency (F_max).
    # -> 'python main.py --sweep': Uses [LOW_PERIOD, HIGH_PERIOD].
    # -> 'python main.py --sweep 1.0 20.0': Uses [1.000, 20.000] ns.
    synthesizer_group.add_argument(
        "--sweep",
        nargs = "*",
        type = float,
        default = None,
        metavar = ("LOW", "HIGH"),
        help = "Execute binary search frequency sweep." \
            " Pass 0 arguments for defaults or 2 bounds:" \
            " LOW HIGH in [ns] (e.g., --sweep 2.0 10.0)."
    )
    
    # Runs code linters.
    parser.add_argument(
        "--lint",
        action = "store_true",
        help = "Run Ruff, Veribe and Verilator linting checks."
    )
    
    # Parses the command-line arguments.
    args: Namespace = parser.parse_args() #TODO ATH

    # ------- Linting. -------
    # 'python main.py --lint'.
    if args.lint:
        print()
        print("Running linters (Ruff, Verible and Verilator)...")

        # IF locally exists, runs Ruff.
        ruff_path: str | None = shutil.which(cmd = "ruff")
        if ruff_path is not None:
            ruff_cmd: list[str] = [
                "ruff",
                "check",
                "."
            ]

            ruff_result: CompletedProcess = subprocess.run(
                ruff_cmd,
                cwd = MAIN_DIR_PATH
            )

            ruff_status: str = "SUCCESS" if ruff_result.returncode == 0 else "FAILED"
            
            print(f"-> [{ruff_status}] Ruff")
        else:
            ruff_status: str = "NOT FOUND"
            print("[NOT FOUND] Ruff not found locally (enforced via GitHub Action 'Ruff').")

        # IF locally exists, runs Verible.
        verible_path: str | None = shutil.which(cmd = "verible-verilog-lint")
        if verible_path is not None:
            verilog_file_paths: list[str] = [str(file_path) for file_path in VERILOG_SRC_FILE_PATHS]

            verible_cmd: list[str] = [
                "verible-verilog-lint",
                "--rules_config",
                ".rules.verible_lint"
            ] + verilog_file_paths

            verible_result: CompletedProcess = subprocess.run(
                verible_cmd,
                cwd = MAIN_DIR_PATH
            )

            verible_status: str = "SUCCESS" if verible_result.returncode == 0 else "FAILED"

            print(f"-> [{verible_status}] Verible")
        else:
            verible_status: str = "NOT FOUND"
            print("[NOT FOUND] Verible not found locally (enforced via GitHub Action 'Verible').")

        # Runs Verilator.
        verilator_executable_path: Path | None = None
    
        try:
            verilator_executable_path = locate_verilator_executable(hardcoded_verilator_path = "D:/Programs/oss-cad-suite")
            verilator_bin_dir: str = str(verilator_executable_path.parent)
    
            if verilator_bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = verilator_bin_dir + os.pathsep + os.environ.get("PATH", "")
        except FileNotFoundError:
            print()
            print("[NOTE] Verilator not found locally (DO-254 linting will be enforced in CI).")
        
        if verilator_executable_path is not None:
            verilator_cmd: list[str] = [
                str(verilator_executable_path),
                "--lint-only",
                "-Wall",
                "-I" + str(RTL_DIR_PATH),
                str(RTL_DIR_PATH/f"{TOP_MODULE}.v")
            ]
            
            verilator_result: CompletedProcess = subprocess.run(
                verilator_cmd,
                cwd = MAIN_DIR_PATH
            )

            verilator_status: str = "SUCCESS" if verilator_result.returncode == 0 else "FAILED"

            print(f"-> [{verilator_status}] Verilator")
        else:
            verilator_status: str = "NOT FOUND"
            print("[NOT FOUND] Verilator not found locally (enforced via GitHub Action 'Verilator').")

        # Checks for failures.
        if (ruff_status != "FAILED") and (verible_status != "FAILED") and (verilator_status != "FAILED"):
            print("--> Linting passed! <--")
        else:
            print("--> Linting failed! <--")
            sys.exit(1)

    # ------- Custom Classes. -------
    # Aircraft Engine (Floating Type).
    config_aircraft_engine_simulator_floating = ConfigAircraftEngineSimulatorFloating(
        simulation_step = cfg.simulation.simulation_step,
        total_simulation_time = cfg.simulation.total_simulation_time,

        ambient_pressure = cfg.ambient.ambient_pressure,
        ambient_temperature = cfg.ambient.ambient_temperature,

        rotor_inertial_time_const = cfg.inertia.rotor_inertial_time_const,
        pressure_volume_time_const = cfg.inertia.pressure_volume_time_const,
        thermal_time_const = cfg.inertia.thermal_time_const,

        speed_gain_coeff = cfg.gain.speed_gain_coeff,
        compressor_pressure_gain = cfg.gain.compressor_pressure_gain,
        combustion_heat_gain = cfg.gain.combustion_heat_gain,
        mass_overflow_cooling_gain = cfg.gain.mass_overflow_cooling_gain,

        max_rotational_speed = cfg.limit.max_rotational_speed,
        max_compressor_temperature = cfg.limit.max_compressor_temperature
    )

    aircraft_engine_simulator_floating = AircraftEngineSimulatorFloating(
        config_aircraft_engine_simulator_floating = config_aircraft_engine_simulator_floating
    )

    # Aircraft Engine (Fixed Point Type).
    #   Quantizes all the attributes from the floating type to the fixed point type.
    config_aircraft_engine_simulator_fixed_point = ConfigAircraftEngineSimulatorFixedPoint(
        int_bit_width = cfg.representation.int_bit_width,
        fractional_bit_width = cfg.representation.fractional_bit_width,

        simulation_step = cfg.simulation.simulation_step,
        total_simulation_time = cfg.simulation.total_simulation_time,
    
        ambient_pressure_quantized =  cfg.ambient.ambient_pressure_quantized,
        ambient_temperature_quantized =  cfg.ambient.ambient_temperature_quantized,
    
        pre_calculated_rotor_inertial_time_const_quantized = cfg.inertia.pre_calculated_rotor_inertial_time_const_quantized,
        pre_calculated_pressure_volume_time_const_quantized = cfg.inertia.pre_calculated_pressure_volume_time_const_quantized,
        pre_calculated_thermal_time_const_quantized = cfg.inertia.pre_calculated_thermal_time_const_quantized,
    
        speed_gain_coeff_quantized = cfg.gain.speed_gain_coeff_quantized,
        compressor_pressure_gain_quantized = cfg.gain.compressor_pressure_gain_quantized,
        combustion_heat_gain_quantized = cfg.gain.combustion_heat_gain_quantized,
        mass_overflow_cooling_gain_quantized = cfg.gain.mass_overflow_cooling_gain_quantized,
    
        max_rotational_speed_quantized = cfg.limit.max_rotational_speed_quantized,
        max_compressor_temperature_quantized = cfg.limit.max_compressor_temperature_quantized,

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
        max_speed = cfg.limit.max_rotational_speed,

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
        initial_conditions = (0.0, cfg.ambient.ambient_pressure,  cfg.ambient.ambient_temperature)
    )

    #: time_history stays stable independent from the representation, so it doesnt need to be returned from floating simulation as well.
    fuel_flow_history_fixed_point, speed_history_fixed_point, pressure_history_fixed_point, temperature_history_fixed_point, is_engine_broken_history, _ = aircraft_engine_simulator_fixed_point.run_simulation(
        initial_conditions = (
            0, 
            cfg.ambient.ambient_pressure_quantized, 
            cfg.ambient.ambient_temperature_quantized
        )
    )

    # Scales the integer values from fixed point representation back to the normal range.
    fixed_point_scale_factor: int = 2 ** cfg.representation.fractional_bit_width
    
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
    #   -> sources: List of paths to the source files.
    #   -> hdl_toplevel: Name of the top-level module.
    #   -> includes: Passes additional search directories.
    #   -> parameters: Dictionary mapping hdl parameters.
    #   -> always: True: Forces a complete recompile every time.
    #             False: Checks file timestamps and skips recompiling if source haven't changed.
    # Compiles the verilog files.
    runner.build(
        sources = VERILOG_SRC_FILE_PATHS,
        hdl_toplevel = TOP_MODULE,
        includes = [RTL_DIR_PATH],
        parameters = COCOTB_PARAMETERS,
        always = True
    )

    # Runs the testbench.
    runner.test(
        hdl_toplevel = TOP_MODULE,
        test_module = "test_engine",
        test_dir = TB_DIR_PATH
    )

    # ------- Synthesis. -------
    # -> 'python main.py --sweep'.
    # -> 'python main.py --sweep 2.0 10.0'.
    if args.sweep is not None:
        # Validates argument count. Either 0 (default) or 2 (customs).
        if len(args.sweep) == 2:
            adjusted_low_period_ns: float = float(min(args.sweep))
            adjusted_high_period_ns: float = float(max(args.sweep))
        elif len(args.sweep) == 0:
            adjusted_low_period_ns = cfg.synthesis.sweep_low_period
            adjusted_high_period_ns = cfg.synthesis.sweep_high_period
        else:
            parser.error(
                message = "--sweep accepts either 0 arguments (using defaults)" \
                    " or exactly 2 bounds: LOW HIGH (e.g., --sweep 2.0 10.0)."
            )

        print()
        print(f"Calculating the maximum frequency by trying periods between [{adjusted_low_period_ns}, {adjusted_high_period_ns}] ns...")

        best_synthesizable_period: float = adjusted_high_period_ns
        best_wns: float = -np.inf

        while ((adjusted_high_period_ns - adjusted_low_period_ns) > 0.100):
            # Calculates the midpoint test period.
            test_period_ns: float = round(((adjusted_high_period_ns + adjusted_low_period_ns) / 2), 3)

            wns: float = synthesis_runner.run_synthesis(
                target_period_ns = test_period_ns,
                should_update_readme = False
            )

            # Updates the period boundaries.
            if (wns >= 0.000):
                adjusted_high_period_ns = test_period_ns
                best_synthesizable_period = test_period_ns
                best_wns = wns
            else:
                adjusted_low_period_ns = test_period_ns

            print(f"-> Period: {test_period_ns} & WNS: {wns}")

        # Re-runs synthesis with the highest frequency to update the README.
        _ = synthesis_runner.run_synthesis(
            target_period_ns = best_synthesizable_period,
            should_update_readme = True
        )

        print()
        print(f" --> Best (Shortest) Period: {best_synthesizable_period} ns | Best (Lowest) WNS: {best_wns} ns")

    elif args.synth is not None:
        target_period: float = args.synth
        print()
        print(f"Running single Out-of-Context synthesis at target period: {target_period} ns...")

        _ = synthesis_runner.run_synthesis(
            target_period_ns = target_period,
            should_update_readme = True
        )

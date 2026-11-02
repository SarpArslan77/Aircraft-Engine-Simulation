
#* test_engine.py

#* ======= Libraries =======
# ------- Native. -------
import json
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

# ------- Externals. -------
#? cocotb (Coroutine-based Co-simulation Testbench environment):
#   Open-source, Python-based hardware verification framework for RTL designs.
import cocotb
import numpy as np
import pandas as pd

#? Clock: Utility class, drives an periodic square-wave signal .
#   - signal: Input clock pin.
#   - period: Total duration of one full clock cycle.
#   - units: Physical unit of time for the period.
from cocotb.clock import Clock
#? SimHandleBase: Abstract class, represents any object, hierarchy node, wire,
#   reg or port inside the simulatrors netlist.
from cocotb.handle import SimHandleBase
#? RisingEdge: Trigger, pauses the Python coroutine until the signal pulses high.
#   - signal: Wire, register or pin object, that gets monitored.
#? ClockCycles: Trigger, pauses the the coroutine until the signal has pulsed.
#   for a given number of active edges.
#   - signal: Clock signal to count edges on.
#   - num_cycles: Total number of clock edges to wait before resuming.
#   - rising: Counts rising edges (True: 0 -> 1 & False: 1 -> 0).
from cocotb.triggers import ClockCycles, RisingEdge
#? cocotbext-axi: It sits on top of Cocotb and abstracts cycle-accurate bus
#   signaling into high-level, asynchronous Python transactions (read and write)
#   with AXI Syntax.
#? AxiLiteBus: Structural container, finds bundles and wraps the physical wires
#   of the Device Under Test (DUT) into single object.
#? AxiLiteMaster: Active controller, simulates a CPU core or bus master driving
#   transactions into the design (which acts like a AXI Slave).
from cocotbext.axi import AxiLiteBus, AxiLiteMaster
from numpy import int64
from numpy.typing import NDArray
from pandas import DataFrame


#* ======= Aircraft Engine Tester's Config Dataclass =======
@dataclass(frozen = True)
class ConfigEngineTester:
    """
    Configuration dataclass holding memory-mapped register offsets and verification parameters.

    Defines the 32-bit Control and Status Register (CSR) bus byte offsets, simulation time steps,
    bit-width formats, safety thresholds, and test durations used by the Cocotb testbench harness.

    Attributes:
        addr_control (int): Byte address offset for the Engine Control Register (0x00).
        addr_status (int): Byte address offset for the read-only Safety Status Register (0x04).
        addr_fuel_flow_command (int): Byte address offset for Commanded Fuel Flow in Q16.16 format (0x08).
        addr_speed (int): Byte address offset for Rotational Speed telemetry in Q16.16 format (0x0C).
        addr_pressure (int): Byte address offset for Compressor Pressure telemetry in Q16.16 format (0x10).
        addr_temperature (int): Byte address offset for Exhaust Gas Temperature telemetry in Q16.16 format (0x14).
        addr_fault_injection (int): Byte address offset for Hardware Fault-Injection Register (0x18).
        software_results_file_path_str (str): Path string to the golden reference CSV dataset.
        simulation_step (float): Discrete integration step size (dt) in seconds [s].
        total_simulation_time (float): Total physical duration of the reference verification cycle [s].
        fractional_bit_width (int): Number of fractional bits used in fixed-point representation.
        max_compressor_temperature (int): Maximum safe temperature limit before emergency trip [°C].
        smoke_test_duration (float): Physical simulation duration for the sanity smoke test [s].
        compressor_stall_test_duration (float): Pre-fault run duration for compressor stall test [s].
        max_thermal_threshold_cross_duration (float): Maximum timeout duration for thermal trip [s].
    """

    # ------- Address Map Offsets. -------
    addr_control: int
    addr_status: int
    addr_fuel_flow_command: int
    addr_speed: int
    addr_pressure: int
    addr_temperature: int
    addr_fault_injection: int

    # ------- Paths. -------
    software_results_file_path_str: str

    # ------- Simulation. -------
    simulation_step: float
    total_simulation_time: float

    fractional_bit_width: int

    # ------- Engine. -------
    max_compressor_temperature: int

    smoke_test_duration: float
    compressor_stall_test_duration: float
    max_thermal_threshold_cross_duration: float

#* ======= Aircraft Engine Tester =======
class EngineTester:
    """
    Cocotb verification testbench harness for the synthesizable aircraft engine RTL core.

    Interfaces with the Device Under Test (DUT) using an AXI4-Lite master bus agent to drive
    control commands, inject hardware faults, sample telemetry registers, and execute cycle-accurate
    hardware-in-the-loop (HIL) verification against Python golden reference models.
    """
    def __init__(
            self,
            config_engine_tester: ConfigEngineTester
    ) -> None:
        """
        Initializes the EngineTester verification harness with testbench configurations.

        Args:
            config_engine_tester (ConfigEngineTester): Configuration dataclass specifying register
                address offsets, simulation step intervals, bit widths, and test execution limits.

        Returns:
            None
        """
        self._cfg: ConfigEngineTester = config_engine_tester

    #? async: Defines a coroutine function.
    async def _perform_synchronous_reset(
            self,
            dut: SimHandleBase,
            axil_master: AxiLiteMaster
    ) -> None:
        """
        Applies an active-low synchronous reset sequence and verifies baseline register health.

        Drives s_axi_aresetn low for 5 clock cycles, releases reset high for 5 clock cycles,
        and reads the status register via AXI4-Lite to confirm normal operational readiness.

        Args:
            dut (SimHandleBase): Handle to the top-level Device Under Test (DUT).
            axil_master (AxiLiteMaster): Cocotb AXI4-Lite master bus controller instance.

        Raises:
            AssertionError: If the status register read after reset returns non-zero.

        Returns:
            None
        """
        # Resets the device.
        dut.s_axi_aresetn.value = 0
        await ClockCycles(
            signal = dut.s_axi_aclk,
            num_cycles = 5
        )

        dut.s_axi_aresetn.value = 1
        await ClockCycles(
            signal = dut.s_axi_aclk,
            num_cycles = 5
        )

        #? _log.info: Logging interface.
        dut._log.info(msg = "Reset complete. Verifying initial status...")

        # Reads the status register (0: engine healthy).
        status_bytes = await axil_master.read(
            address = self._cfg.addr_status,
            length = 4    
        )
        status_s16: int = int.from_bytes(
            status_bytes,
            "little",
            signed = True
        )
        
        assert (status_s16 == 0), f"Expected status '0' after reset, got {status_s16}"
        dut._log.info(msg = "Status register verified: 0 (Normal)")

    async def _start_engine(
            self,
            axil_master: AxiLiteMaster,
            dut: SimHandleBase
    ) -> None:
        """
        Commands engine ignition over AXI4-Lite and synchronizes to the next integration domain clock.

        Writes to the control register asserting the start_engine bit (Bit 0) and pauses execution
        until the prescaled domain clock enable pulse (clk_en_1ms) is asserted.

        Args:
            axil_master (AxiLiteMaster): Cocotb AXI4-Lite master bus controller instance.
            dut (SimHandleBase): Handle to the top-level Device Under Test (DUT).

        Returns:
            None
        """
        # Starts the engine.
        await axil_master.write(
            address = self._cfg.addr_control,
            data = (1).to_bytes(
                4,
                "little",
                signed = True
            )  
        )
        dut._log.info(msg = "Engine start commanded!")

        # Waits for 1 tick so the hardware officially enters running state.
        while True:
            await RisingEdge(dut.s_axi_aclk)
            if (dut.clk_en_1ms.value == 1): 
                break

    # ------- The Smoke Test. -------
    async def run_smoke_test(
            self,
            dut: SimHandleBase
    ) -> None:
        """
        Executes an end-to-end basic functional sanity and smoke test sequence on the RTL engine.

        Verification Steps:
        1. Starts an asynchronous 100 MHz clock (10 ns period) on s_axi_aclk.
        2. Applies synchronous active-low reset and confirms initial zero status.
        3. Performs a loopback write/read check on the commanded fuel flow register.
        4. Commands engine ignition via the control register.
        5. Advances time across the configured smoke test duration via clk_en_1ms pulses.
        6. Reads and logs scaled real-time telemetry (Speed, Pressure, Temperature).

        Args:
            dut (SimHandleBase): Handle to the top-level Device Under Test (DUT).

        Raises:
            AssertionError: If reset status is non-zero or the fuel flow register fails loopback.

        Returns:
            None
        """
        #? cocotb.start_soon(): Task scheduler, launches an asynchronous coroutine
        #   in the background (concurenntly).
        # Starts a 100 MhZ clock (10 ns period).
        cocotb.start_soon(
            Clock(dut.s_axi_aclk, 10, "ns").start()
        )

        # Declares the AXI4-Lite module.
        axil_bus = AxiLiteBus.from_prefix(
            entity = dut,
            prefix = "s_axi"
        )
        
        axil_master = AxiLiteMaster(
            bus = axil_bus,
            clock = dut.s_axi_aclk,
            reset = dut.s_axi_aresetn,
            reset_active_level = False
        )

        #?  .write_if.log.setLevel(): Changes the read log messages categories.
        #?  .read_if.log.setLevel(): Changes the read log messages categories.
        # Adjusts the log level of axi lite masters read and write interfaces.
        axil_master.write_if.log.setLevel(level = logging.WARNING)
        axil_master.read_if.log.setLevel(level = logging.WARNING)

        # Resets the device.
        await self._perform_synchronous_reset(
            dut = dut,
            axil_master = axil_master    
        )

        # Writes to fuel command register (10 kg/h in Q16.16 = 10 << 16).
        fuel_command_s16: int = 10 << self._cfg.fractional_bit_width
        fuel_command_bytes: bytes = fuel_command_s16.to_bytes(
            4,
            "little",
            signed = True
        )

        await axil_master.write(
            address = self._cfg.addr_fuel_flow_command,
            data = fuel_command_bytes    
        )

        # Reads it back to verify, that the register stored it.
        read_fuel_value_bytes = await axil_master.read(
            address = self._cfg.addr_fuel_flow_command,
            length = 4
        )
        read_fuel_value_s16: int = int.from_bytes(
            read_fuel_value_bytes,
            "little",
            signed = True    
        )

        assert (read_fuel_value_s16 == fuel_command_s16), f"Fuel mismatch! Wrote {fuel_command_s16}, got {read_fuel_value_s16}"
        dut._log.info(msg = f"Fuel command register verified: {read_fuel_value_s16 >> 16} kg/h")

        # Starts the engine (a.k.a. sets the bit '0' in control register).
        await axil_master.write(
            address = self._cfg.addr_control,
            data = (1).to_bytes(
                4,
                "little",
                signed = True
            ) 
        )
        dut._log.info(msg = "Engine start commanded! Running simulation...") 

        # Waits for Euoler integration cycles.
        smoke_test_cycle: int = round(self._cfg.smoke_test_duration / self._cfg.simulation_step)

        for _ in range(smoke_test_cycle):
            await RisingEdge(dut.clk_en_1ms)

        # Reads the data back over the bus.
        read_speed_value_bytes = await axil_master.read(
            address = self._cfg.addr_speed,
            length = 4    
        )
        read_speed_value_s16: int = int.from_bytes(
            read_speed_value_bytes,
            "little",
            signed = True    
        )

        read_pressure_value_bytes = await axil_master.read(
            address = self._cfg.addr_pressure,
            length = 4    
        )
        read_pressure_value_s16: int = int.from_bytes(
            read_pressure_value_bytes,
            "little",
            signed = True    
        )

        read_temperature_value_bytes = await axil_master.read(
            address = self._cfg.addr_temperature,
            length = 4    
        )
        read_temperature_value_s16: int = int.from_bytes(
            read_temperature_value_bytes,
            "little",
            signed = True    
        )

        # Scales back the read-values to normal intervalls.
        speed_scaled: float = read_speed_value_s16 / (1 << self._cfg.fractional_bit_width)
        pressure_scaled: float = read_pressure_value_s16 / (1 << self._cfg.fractional_bit_width)
        temperature_scaled: float = read_temperature_value_s16 / (1 << self._cfg.fractional_bit_width)

        # Logs the results.
        dut._log.info(f"Read-Data: Speed: {speed_scaled:.2f}, Pressure: {pressure_scaled:.2f} kPa, Temperature: {temperature_scaled} *C")

        dut._log.info("Smoke test PASSED successfully!")

    # ------- Golden Reference Verification Test. -------
    async def run_golden_reference_verification_test(
            self,
            dut: SimHandleBase
    ) -> None:
        """
        Executes a bit-for-bit cycle-accurate verification test against the software reference model.

        Verification Steps:
        1. Resets the DUT and commands engine ignition via AXI4-Lite.
        2. Loads the golden reference trajectory dataset from the software results CSV file.
        3. Steps synchronously through every discrete time interval:
        - Writes commanded fuel flow into the hardware register via AXI4-Lite.
        - Waits for the 1 ms discrete solver tick (clk_en_1ms).
        - Reads hardware telemetry registers (Speed, Pressure, Temperature, Status).
        - Asserts that hardware outputs match golden reference values within quantization tolerance.

        Args:
            dut (SimHandleBase): Handle to the top-level Device Under Test (DUT).

        Raises:
            AssertionError: If any hardware telemetry state diverges by 2 or more LSBs from the
                golden reference dataset, or if the emergency trip status flag mismatches.

        Returns:
            None
        """
        # Starts a 100 MhZ clock.
        cocotb.start_soon(
            Clock(dut.s_axi_aclk, 10, "ns").start()
        )

        # Declares the AXI4-Lite module.
        axil_bus = AxiLiteBus.from_prefix(
            entity = dut,
            prefix = "s_axi"
        )
        
        axil_master = AxiLiteMaster(
            bus = axil_bus,
            clock = dut.s_axi_aclk,
            reset = dut.s_axi_aresetn,
            reset_active_level = False
        )

        # Adjusts the log level of axi lite masters read and write interfaces.
        axil_master.write_if.log.setLevel(level = logging.WARNING)
        axil_master.read_if.log.setLevel(level = logging.WARNING)
    
        # Resets the device.
        await self._perform_synchronous_reset(
            dut = dut,
            axil_master = axil_master    
        )

        # Starts the engine.
        await self._start_engine(
            axil_master = axil_master,
            dut = dut
        )

        # Loads the golden reference dataset.
        software_results_df: DataFrame = pd.read_csv(self._cfg.software_results_file_path_str)

        fuel_flow_col: NDArray[int64] = software_results_df["fuel_flow"].values
        speed_col: NDArray[int64]  = software_results_df["speed"].values
        pressure_col: NDArray[int64]  = software_results_df["pressure"].values
        temperature_col: NDArray[int64] = software_results_df["temperature"].values
        is_engine_broken_col: NDArray[int64]  = software_results_df["is_engine_broken"].values

        total_steps = int(
            np.ceil(self._cfg.total_simulation_time / self._cfg.simulation_step)
        )

        for i in range(total_steps+1):
            # Writes the fuel flow values for the current step.
            fuel_flow_bytes: bytes = int(fuel_flow_col[i]).to_bytes(
                4,
                "little",
                signed = True
            )

            await axil_master.write(
                address = self._cfg.addr_fuel_flow_command,
                data = fuel_flow_bytes
            )

            # Advances clock cycles until domain clock pulses.
            while True:
                await RisingEdge(dut.s_axi_aclk)
                if (dut.clk_en_1ms.value == 1): 
                    break

            # Reads the hardware registers.
            hardware_speed_result_bytes = await axil_master.read(
                address = self._cfg.addr_speed,
                length = 4    
            )
            hardware_speed_result_s16: int = int.from_bytes(
                hardware_speed_result_bytes,
                "little",
                signed = True    
            )

            hardware_pressure_result_bytes = await axil_master.read(
                address = self._cfg.addr_pressure,
                length = 4    
            )
            hardware_pressure_result_s16: int = int.from_bytes(
                hardware_pressure_result_bytes,
                "little",
                signed = True    
            )

            hardware_temperature_result_bytes = await axil_master.read(
                address = self._cfg.addr_temperature,
                length = 4    
            )
            hardware_temperature_result_s16: int = int.from_bytes(
                hardware_temperature_result_bytes,
                "little",
                signed = True    
            )

            hardware_is_engine_broken_result_bytes = await axil_master.read(
                address = self._cfg.addr_status,
                length = 4    
            )
            hardware_is_engine_broken_result_s16: int = int.from_bytes(
                hardware_is_engine_broken_result_bytes,
                "little",
                signed = True    
            )

            # Compares the results.
            assert (abs(hardware_speed_result_s16 - speed_col[i]) < 2), \
                f"speed: {hardware_speed_result_s16} vs. {speed_col[i]}"
            assert (abs(hardware_pressure_result_s16 - pressure_col[i]) < 2), \
                f"pressure: {hardware_pressure_result_s16} vs. {pressure_col[i]}"
            assert (abs(hardware_temperature_result_s16 - temperature_col[i]) < 2), \
                f"temperature: {hardware_temperature_result_s16} vs. {temperature_col[i]}"
            assert (hardware_is_engine_broken_result_s16 == is_engine_broken_col[i]), \
                f"is_engine_broken: {hardware_is_engine_broken_result_s16} vs. {is_engine_broken_col[i]}"

    async def run_compressor_stall_test(
            self,
            dut: SimHandleBase
    ) -> None:
        """
        Executes a safety-critical fault injection test simulating a turbine compressor stall.

        Verification Steps:
        1. Resets and ignites the engine, commanding high military fuel flow (90 kg/h).
        2. Allows the engine to stabilize into a steady running state.
        3. Writes to the fault-injection register asserting Bit 0 (fault_compressor_stall, K_cool -> 0).
        4. Monitors real-time exhaust gas temperature until it breaches max_compressor_temperature.
        5. Reads the status register and verifies the supervisory FSM entered the EMERGENCY trip state.

        Args:
            dut (SimHandleBase): Handle to the top-level Device Under Test (DUT).

        Raises:
            AssertionError: If register loopback fails or the status register fails to flag broken state.
            TimeoutError: If exhaust temperature fails to exceed the safety threshold within
                the maximum timeout cycle window.

        Returns:
            None
        """
        # Starts a 100 MhZ clock.
        cocotb.start_soon(
            Clock(dut.s_axi_aclk, 10, "ns").start()
        )

        # Declares the AXI4-Lite module.
        axil_bus = AxiLiteBus.from_prefix(
            entity = dut,
            prefix = "s_axi"
        )

        axil_master = AxiLiteMaster(
            bus = axil_bus,
            clock = dut.s_axi_aclk,
            reset = dut.s_axi_aresetn,
            reset_active_level = False
        )

        # Adjusts the log level of axi lite masters read and write interfaces.
        axil_master.write_if.log.setLevel(level = logging.WARNING)
        axil_master.read_if.log.setLevel(level = logging.WARNING)
        
        # Resets the device.
        await self._perform_synchronous_reset(
            dut = dut,
            axil_master = axil_master    
        )
        
        # Starts the engine.
        await self._start_engine(
            axil_master = axil_master,
            dut = dut
        )

        # Writes to fuel command register (90 kg/h in Q16.16 = 90 << 16).
        fuel_command_s16: int = 90 << self._cfg.fractional_bit_width
        fuel_command_bytes: bytes = fuel_command_s16.to_bytes(
            4,
            "little",
            signed = True
        )

        await axil_master.write(
            address = self._cfg.addr_fuel_flow_command,
            data = fuel_command_bytes
        )
        
        # Reads it back to verify, that the register stored it.
        read_fuel_value_bytes = await axil_master.read(
            address = self._cfg.addr_fuel_flow_command,
            length = 4
        )
        read_fuel_value_s16: int = int.from_bytes(
            read_fuel_value_bytes,
            "little",
            signed = True
        )

        assert (read_fuel_value_s16 == fuel_command_s16), f"Fuel mismatch! Wrote {fuel_command_s16}, got {read_fuel_value_s16}"
        dut._log.info(msg = f"Fuel command register verified: {read_fuel_value_s16 >> 16} kg/h")

        # Waits for Euoler integration cycles.
        compressor_stall_test_cycle: int = round(self._cfg.compressor_stall_test_duration / self._cfg.simulation_step)

        for _ in range(compressor_stall_test_cycle): 
            await RisingEdge(dut.clk_en_1ms)

        # Injects the fault.
        await axil_master.write(
            address = self._cfg.addr_fault_injection,
            data = (1).to_bytes(
                4,
                "little",
                signed = True
            )     
        )

        # Waits for the temperature to raise and engine to break.
        is_thermal_threshold_crossed: bool = False

        max_thermal_threshold_cross_cycle: int = round(self._cfg.max_thermal_threshold_cross_duration / self._cfg.simulation_step)
        thermal_threshold_cross_cycle: int = 0

        while not is_thermal_threshold_crossed:
            await RisingEdge(dut.clk_en_1ms)
            thermal_threshold_cross_cycle += 1

            # Reads the temperature.
            read_temperature_value_bytes = await axil_master.read(
                address = self._cfg.addr_temperature,
                length = 4
            )
            read_temperature_value_s16: int = int.from_bytes(
                read_temperature_value_bytes,
                "little",
                signed = True
            )
            read_temperature_value_scaled: float = read_temperature_value_s16 / (1 << self._cfg.fractional_bit_width)

            # Checks red-temperature value is greater then thermal limit. 
            if (read_temperature_value_scaled > self._cfg.max_compressor_temperature):
                is_thermal_threshold_crossed = True

                dut._log.info(msg = f"Thermal limit reached: {read_temperature_value_scaled}")

            # Safety mechanism, stops the loop if it passes its maximum time threshold.
            if (thermal_threshold_cross_cycle >= max_thermal_threshold_cross_cycle) and not is_thermal_threshold_crossed:
                raise TimeoutError(f"Timeout! Engine failed to trip within {max_thermal_threshold_cross_cycle} cycles.")

        # Waits one tick for the FSM to latch the trip state.
        await RisingEdge(dut.clk_en_1ms)
        
        # Reads the engine status.
        read_engine_status_value_bytes = await axil_master.read(
            address = self._cfg.addr_status,
            length = 4    
        )
        read_engine_status_value_s16: int = int.from_bytes(
            read_engine_status_value_bytes,
            "little",
            signed = True    
        )

        # Checks red-status value is equals to a broken engine.
        assert (read_engine_status_value_s16 == 1), \
            f"Engine did not break! Current status: {read_engine_status_value_s16}"
        dut._log.info(msg = f"Engine broke! Status: {read_engine_status_value_s16}")

#* ======= Helper Functions =======
# ------- JSON Loader. -------
def load_config() -> dict[str, Any]:
    """
    Loads and parses the testbench JSON configuration file.

    Resolves the configuration file path relative to the test directory to ensure
    consistent loading regardless of whether the simulator changes the working directory.

    Returns:
        dict[str, Any]: Parsed configuration dictionary mapping test module stems
            to their respective parameter dictionaries.
    """
    # Imports the JSON file.
    #? When Cocotb executes the tests through the runner, it switches the
    #   current working directory to the simulators output folder 'sim_build'.
    #   --> Absolute path has to be passed and not just json file name.
    MAIN_DIR_PATH: Path = Path(__file__).resolve().parent
    JSON_FILE_PATH: Path = MAIN_DIR_PATH / "config.json" #TODO FH
    
    with open(
        file = JSON_FILE_PATH, 
        mode = "r",
        encoding = "utf-8"
    ) as f:
        config: dict[str, dict[str, Any]] = json.load(f)

    return config

#* ======= Cocotb Test Entry Points =======
#? @cocotb.test(): Function decorator, registers an 'async def' function
#   as an official executable test case in the verification suite.
@cocotb.test()
async def test_engine_smoke(dut: SimHandleBase) -> None:
    """
    Cocotb entry point test case verifying RTL engine synthesis sanity and bus connectivity.

    Loads configuration parameters, initializes the EngineTester harness, and executes
    the basic operational smoke test sequence through the Cocotb task scheduler.

    Args:
        dut (SimHandleBase): Handle to the top-level synthesizable Verilog module
            ('aircraft_engine_simulator_top') injected by Cocotb.

    Returns:
        None
    """
    # Loads the config file.
    config: dict[str, Any] = load_config()

    # Extracts the current files parameters from the JSON file.
    #? .stem: Retrieves the active file names, without the extension.
    active_file_name: str = Path(__file__).stem
    active_file_config: dict = config[active_file_name]
    
    config_engine_tester = ConfigEngineTester(**active_file_config)

    tester = EngineTester(config_engine_tester = config_engine_tester)
    
    await tester.run_smoke_test(dut = dut)

@cocotb.test()
async def test_engine_golden_reference(dut: SimHandleBase) -> None:
    """
    Cocotb entry point test case verifying hardware telemetry against golden software traces.

    Executes a full mission throttle cycle step-by-step, validating that the synthesizable
    Verilog Euler integrator reproduces the Python fixed-point model within strict bit tolerances.

    Args:
        dut (SimHandleBase): Handle to the top-level synthesizable Verilog module
            ('aircraft_engine_simulator_top') injected by Cocotb.

    Returns:
        None
    """
    # Loads the config file.
    config: dict[str, Any] = load_config()
    
    # Extracts the current file's parameters from the JSON file.
    active_file_name: str = Path(__file__).stem
    active_file_config: dict = config[active_file_name]
    
    config_engine_tester = ConfigEngineTester(**active_file_config)
    
    tester = EngineTester(config_engine_tester = config_engine_tester)

    await tester.run_golden_reference_verification_test(dut = dut)

@cocotb.test()
async def test_engine_compressor_stall_test(dut: SimHandleBase) -> None:
    """
    Cocotb entry point test case verifying safety shutdown logic under fault injection.

    Commands maximum throttle, triggers a virtual compressor stall fault via AXI4-Lite,
    and verifies thermal runaway detection and automatic emergency fuel cut-off FSM tripping.

    Args:
        dut (SimHandleBase): Handle to the top-level synthesizable Verilog module
            ('aircraft_engine_simulator_top') injected by Cocotb.

    Returns:
        None
    """
    # Loads the config file.
    config: dict[str, Any] = load_config()

    # Extracts the current file's parameters from the JSON file.
    active_file_name: str = Path(__file__).stem
    active_file_config: dict = config[active_file_name]

    config_engine_tester = ConfigEngineTester(**active_file_config)

    tester = EngineTester(config_engine_tester = config_engine_tester)
    
    await tester.run_compressor_stall_test(dut = dut)
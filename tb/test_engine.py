
#* test_engine.py

#* ======= Libraries =======
# ------- Native. -------
import json
from dataclasses import dataclass
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
#TODO AC
from cocotbext.axi import AxiLiteBus, AxiLiteMaster
from numpy import int64
from numpy.typing import NDArray
from pandas import DataFrame


#* ======= Aircraft Engine Tester's Config Dataclass =======
@dataclass(frozen = True)
class ConfigEngineTester:
    """
    Configuration dataclass holding memory-mapped register address offsets.

    Defines the standard 32-bit Control and Status Register (CSR) bus offsets
    used by the Cocotb verification harness to communicate with the hardware
    register interface over standard VPI.

    Attributes:
        addr_control (int): Byte address offset for the primary Engine Control Register (0x00).
        addr_status (int): Byte address offset for the read-only Safety Status Register (0x04).
        addr_fuel_flow_command (int): Byte address offset for the commanded Fuel Flow Register in Q16.16 format (0x08).
        addr_speed (int): Byte address offset for reading the telemetry Rotational Speed Register in Q16.16 format (0x0C).
        addr_pressure (int): Byte address offset for reading the telemetry Compressor Pressure Register in Q16.16 format (0x10).
        addr_temperature (int): Byte address offset for reading the telemetry Exhaust Gas Temperature Register in Q16.16 format (0x14).
        addr_fault_injection (int): Byte address offset for activating internal hardware fault-injection bits (0x18).
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
    software_results_file_path_str: Path

    # ------- Simulation. -------
    simulation_step: float
    total_simulation_time: float

    # ------- Engine Limits. -------
    max_compressor_temperature: int

#* ======= Aircraft Engine Tester =======
class EngineTester:
    def __init__(
            self,
            config_engine_tester: ConfigEngineTester
    ) -> None:
        """
        Initializes the EngineTester verification harness with memory map configurations.

        Args:
            config_engine_tester (ConfigEngineTester): 
                The configuration dataclass instance specifying the register interface 
                memory-mapped address offsets.
        """

        self._cfg: ConfigEngineTester = config_engine_tester

    #? async: Defines a coroutine function.
    async def _perform_synchronous_reset(
            self,
            dut: SimHandleBase,
            axil_master: AxiLiteMaster
    ) -> None:
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
        status_bytes: bytes = await axil_master.read(
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
        # Starts the engine.
        await axil_master.write(
            address = self._cfg.addr_control,
            data = 1  
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

        The test sequence verifies baseline hardware functionality:
        1. Instantiates and launches an asynchronous 100 MHz simulation clock (10 ns period).
        2. Applies an active-high synchronous reset sequence for 5 clock cycles.
        3. Polls the engine status register to confirm baseline healthy operational state (status = 0).
        4. Writes a 10 kg/h idle fuel flow command in fixed-point Q16.16 format and verifies loopback read.
        5. Commands engine ignition by asserting Bit 0 of the Control Register (start_engine).
        6. Advances discrete simulation time across 50 clock cycles to allow Euler integration.
        7. Reads back real-time engine telemetry (Speed, Pressure, Temperature) via the bus,
           scales the raw Q16.16 integers back to engineering units, and logs formatted output.

        Args:
            dut (SimHandleBase): Handle to the top-level Device Under Test (DUT).

        Raises:
            AssertionError: If initial status is non-zero or if the fuel command register
                            fails to store and return the commanded fixed-point value.

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

        # Resets the device.
        await self._perform_synchronous_reset(
            dut = dut,
            axil_master = axil_master    
        )

        # Writes to fuel command register (10 kg/h in Q16.16 = 10 << 16).
        fuel_command_s16: int = 10 << 16 #TODO FTH
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
        read_fuel_value_bytes: bytes = axil_master.read(
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
            data = 1
        )
        dut._log.info(msg = "Engine start commanded! Running simulation for 50 cycles ...") #TODO FTH

        # Waits for Euoler integration cycles.
        for _ in range(50):
            await RisingEdge(dut.clk_en_1ms)

        # Reads the data back over the bus.
        read_speed_value_bytes: bytes = await axil_master.read(
            address = self._cfg.addr_speed,
            length = 4    
        )
        read_speed_value_s16: int = int.from_bytes(
            read_speed_value_bytes,
            "little",
            signed = True    
        )

        read_pressure_value_bytes: bytes = await axil_master.read(
            address = self._cfg.addr_pressure,
            length = 4    
        )
        read_pressure_value_s16: int = int.from_bytes(
            read_pressure_value_bytes,
            "little",
            signed = True    
        )

        read_temperature_value_bytes: bytes = await axil_master.read(
            address = self._cfg.addr_temperature,
            length = 4    
        )
        read_temperature_value_s16: int = int.from_bytes(
            read_temperature_value_bytes,
            "little",
            signed = True    
        )

        # Scales back the read-values to normal intervalls.
        speed_scaled: float = read_speed_value_s16 / (1 << 16)
        pressure_scaled: float = read_pressure_value_s16 / (1 << 16)
        temperature_scaled: float = read_temperature_value_s16 / (1 << 16)

        # Logs the results.
        dut._log.info(f"Read-Data: Speed: {speed_scaled:.2f}, Pressure: {pressure_scaled:.2f} kPa, Temperature: {temperature_scaled} *C")

        dut._log.info("Smoke test PASSED successfully!")

    # ------- Golden Reference Verification Test. -------
    async def run_golden_reference_verification_test(
            self,
            dut: SimHandleBase
    ) -> None:
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

        fuel_flow_col_bytes: NDArray = software_results_df["fuel_flow"].values.tobytes() #TODO What is a type hint for this
        speed_col_bytes: NDArray  = software_results_df["speed"].values.tobytes()
        pressure_col_bytes: NDArray  = software_results_df["pressure"].values.tobytes()
        temperature_col_bytes: NDArray = software_results_df["temperature"].values.tobytes()
        is_engine_broken_col_bytes: NDArray  = software_results_df["is_engine_broken"].values.tobytes()

        total_steps = int(
            np.ceil(self._cfg.total_simulation_time / self._cfg.simulation_step)
        )

        for i in range(total_steps+1):
            # Writes the fuel flow values for the current step.
            await axil_master.write(
                address = self._cfg.addr_fuel_flow_command,
                data = fuel_flow_col_bytes[i]
            )

            # Advances clock cycles until domain clock pulses.
            while True:
                await RisingEdge(dut.s_axi_aclk)
                if (dut.clk_en_1ms.value == 1): 
                    break

            # Reads the hardware registers.
            hardware_speed_result_bytes: bytes = await axil_master.read(
                address = self._cfg.addr_speed,
                length = 4    
            )
            hardware_speed_result_s16: int = int.from_bytes(
                hardware_speed_result_bytes,
                "little",
                signed = True    
            )

            hardware_pressure_result_bytes: bytes = await axil_master.read(
                address = self._cfg.addr_pressure,
                length = 4    
            )
            hardware_pressure_result_s16: int = int.from_bytes(
                hardware_pressure_result_bytes,
                "little",
                signed = True    
            )

            hardware_temperature_result_bytes: bytes = await axil_master.read(
                address = self._cfg.addr_temperature,
                length = 4    
            )
            hardware_temperature_result_s16: int = int.from_bytes(
                hardware_temperature_result_bytes,
                "little",
                signed = True    
            )

            hardware_is_engine_broken_result_bytes: bytes = await axil_master.read(
                address = self._cfg.addr_is_engine_broken,
                length = 4    
            )
            hardware_is_engine_broken_result_s16: int = int.from_bytes(
                hardware_is_engine_broken_result_bytes,
                "little",
                signed = True    
            )

            # Compares the results.
            assert (abs(hardware_speed_result_s16 - speed_col_bytes[i]) < 2), \
                f"speed: {hardware_speed_result_s16} vs. {speed_col_bytes[i]}"
            assert (abs(hardware_pressure_result_s16 - pressure_col_bytes[i]) < 2), \
                f"pressure: {hardware_pressure_result_s16} vs. {pressure_col_bytes[i]}"
            assert (abs(hardware_temperature_result_s16 - temperature_col_bytes[i]) < 2), \
                f"temperature: {hardware_temperature_result_s16} vs. {temperature_col_bytes[i]}"
            assert (hardware_is_engine_broken_result_s16 == is_engine_broken_col_bytes[i]), \
                f"is_engine_broken: {hardware_is_engine_broken_result_s16} vs. {is_engine_broken_col_bytes[i]}"

    async def run_compressor_stall_test(
            self,
            dut: SimHandleBase
    ) -> None:
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
        fuel_command_s16: int = 90 << 16 #TODO FTH
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
        read_fuel_value_bytes: bytes = await axil_master.read(
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
        for _ in range(500): #TODO FTH
            await RisingEdge(dut.clk_en_1ms)

        # Injects the fault.
        await axil_master.write(
            address = self._cfg.addr_fault_injection,
            data = 1    
        )

        # Waits for the temperature to raise and engine to break.
        for _ in range(5000): #TODO Optimize this by calculating how many cycles it takes to break.
            await RisingEdge(dut.clk_en_1ms)

        # Reads the temperature.
        read_temperature_value_bytes: bytes = await axil_master.read(
            address = self._cfg.addr_temperature,
            length = 4
        )
        read_temperature_value_s16: int = int.from_bytes(
            read_temperature_value_bytes,
            "little",
            signed = True
        )
        read_temperature_value_scaled: int = (read_temperature_value_s16 >> 16) #TODO FTH

        # Checks red-temperature value is greater then thermal limit.
        assert (read_temperature_value_scaled > self._cfg.max_compressor_temperature), \
            f"Thermal limit not reached! Maximum allowed temperature {self._cfg.max_compressor_temperature}, read-value {read_temperature_value_scaled}"
        dut._log.info(msg = f"Thermal limit reached: {read_temperature_value_scaled}")

        # Reads the engine status.
        read_engine_status_value_bytes: bytes = await axil_master.read(
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

    Sets up the register map configuration, instantiates the EngineTester testbench harness,
    and coordinates execution of the basic functional smoke test through the Cocotb scheduler.

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
    
    config_engine_tester = ConfigEngineTester( #TODO Automate this json file extraction with already defined parameter names.
        addr_control = active_file_config["addr_control"],
        addr_status = active_file_config["addr_status"],
        addr_fuel_flow_command = active_file_config["addr_fuel_flow_command"],
        addr_speed = active_file_config["addr_speed"],
        addr_pressure = active_file_config["addr_pressure"],
        addr_temperature = active_file_config["addr_temperature"],
        addr_fault_injection = active_file_config["addr_fault_injection"],

        software_results_file_path_str = active_file_config["software_results_file_path_str"],

        simulation_step = active_file_config["simulation_step"],
        total_simulation_time = active_file_config["total_simulation_time"],

        max_compressor_temperature = active_file_config["max_compressor_temperature"]
    )

    tester = EngineTester(config_engine_tester = config_engine_tester)
    
    await tester.run_smoke_test(dut = dut)

@cocotb.test()
async def test_engine_golden_reference(dut: SimHandleBase) -> None:
    # Loads the config file.
    config: dict[str, Any] = load_config()
    
    # Extracts the current file's parameters from the JSON file.
    active_file_name: str = Path(__file__).stem
    active_file_config: dict = config[active_file_name]
    
    config_engine_tester = ConfigEngineTester( #TODO Automate this json file extraction with already defined parameter names.
        addr_control = active_file_config["addr_control"],
        addr_status = active_file_config["addr_status"],
        addr_fuel_flow_command = active_file_config["addr_fuel_flow_command"],
        addr_speed = active_file_config["addr_speed"],
        addr_pressure = active_file_config["addr_pressure"],
        addr_temperature = active_file_config["addr_temperature"],
        addr_fault_injection = active_file_config["addr_fault_injection"],
    
        software_results_file_path_str = active_file_config["software_results_file_path_str"],
    
        simulation_step = active_file_config["simulation_step"],
        total_simulation_time = active_file_config["total_simulation_time"],

        max_compressor_temperature = active_file_config["max_compressor_temperature"]
    )
    
    tester = EngineTester(config_engine_tester = config_engine_tester)

    await tester.run_golden_reference_verification_test(dut = dut)

@cocotb.test()
async def test_engine_compressor_stall_test(dut: SimHandleBase) -> None:
    # Loads the config file.
    config: dict[str, Any] = load_config()

    # Extracts the current file's parameters from the JSON file.
    active_file_name: str = Path(__file__).stem
    active_file_config: dict = config[active_file_name]

    config_engine_tester = ConfigEngineTester( #TODO Automate this json file extraction with already defined parameter names.
        addr_control = active_file_config["addr_control"],
        addr_status = active_file_config["addr_status"],
        addr_fuel_flow_command = active_file_config["addr_fuel_flow_command"],
        addr_speed = active_file_config["addr_speed"],
        addr_pressure = active_file_config["addr_pressure"],
        addr_temperature = active_file_config["addr_temperature"],
        addr_fault_injection = active_file_config["addr_fault_injection"],
    
        software_results_file_path_str = active_file_config["software_results_file_path_str"],
    
        simulation_step = active_file_config["simulation_step"],
        total_simulation_time = active_file_config["total_simulation_time"],
    
        max_compressor_temperature = active_file_config["max_compressor_temperature"]
    )

    tester = EngineTester(config_engine_tester = config_engine_tester)
    
    await tester.run_compressor_stall_test(dut = dut)
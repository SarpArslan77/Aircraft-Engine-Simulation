
#* test_engine.py

#* ======= Libraries =======
# ------- Native. -------
from dataclasses import dataclass

# ------- Externals. -------
#TODO AC
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import (
    RisingEdge,
    ClockCycles
)
from cocotb.handle import SimHandleBase

#* ======= Aircraft Engine Tester's Config Dataclass =======
@dataclass(frozen = True)
class ConfigEngineTester:
    # ------- Address Map Offsets. -------
    addr_control: int
    addr_status: int
    addr_fuel_flow_command: int
    addr_speed: int
    addr_pressure: int
    addr_temperature: int
    addr_fault_injection: int

#* ======= Aircraft Engine Tester =======
class EngineTester:
    def __init__(
            self,
            config_engine_tester: ConfigEngineTester
    ) -> None:
        self.cfg: ConfigEngineTester = config_engine_tester

    async def _bus_write(
            self,
            dut: SimHandleBase,
            addr: int,
            data: int
    ) -> None:
        await RisingEdge(dut.clk)
        dut.bus_addr.value = addr
        dut.bus_wdata.value = data
        dut.bus_write_en.value = 1
        dut.bus_read_en.value = 0

        await RisingEdge(dut.clk)
        dut.bus_write_en.value = 0

    async def _bus_read(
            self,
            dut: SimHandleBase,
            addr: int
    ) -> int:
        await RisingEdge(dut.clk)
        dut.bus_addr.value = addr
        dut.bus_read_en.value = 1
        dut.bus_write_en.value = 0

        await RisingEdge(dut.clk)
        dut.bus_read_en.value = 0

        # Reads the data returned on the next cycle.
        await RisingEdge(dut.clk)

        return int(dut.bus_rdata.value)

    # ------- The Smoke Test. -------
    @cocotb.test()
    async def test_engine_smoke(
        self,
        dut: SimHandleBase
    ) -> None:
        # Starts a 100 MhZ clock (10 ns period).
        cocotb.start_soon(
            Clock(dut.clk, 10, "ns").start()
        )

        # Resets the device.
        dut.rst.value = 1
        dut.bus_write_en.value = 0
        dut.bus_read_en.value = 0
        dut.bus_addr.value = 0
        dut.bus_wdata.value = 0
        await ClockCycles(
            signal = dut.clk,
            num_cycles = 5
        )
        dut.rst.value = 0
        await ClockCycles(
            signal = dut.clk,
            num_cycles = 5
        )

        dut._log.info(msg = "Reset complete. Verifying initial status...")

        # Reads the status register (0: engine healthy).
        status: int = await self._bus_read(
            dut = dut,
            addr = self.cfg.addr_status
        )
        assert (status == 0), f"Expected status '0' after reset, got {status}"
        dut._log.info(msg = "Status register verified: 0 (Normal)")

        # Writes to fuel command register (10 kg/h in Q16.16 = 10 << 16).
        fuel_command_q16: int = 10 << 16 #TODO FTH
        await self._bus_write(
            dut = dut,
            addr = self.cfg.addr_fuel_flow_command,
            data = fuel_command_q16
        )

        # Reads it back to verify, that the register stored it.
        read_fuel_value: int = await self._bus_read(
            dut = dut,
            addr = self.cfg.addr_fuel_flow_command
        )
        assert (read_fuel_value == fuel_command_q16), f"Fuel mismatch! Wrote {fuel_command_q16}, got {read_fuel_value}"
        dut._log.info(msg = f"Fuel command register verified: {read_fuel_value >> 16} kg/h")

        # Starts the engine (a.k.a. sets the bit '0' in control register).
        await self._bus_write(
            dut = dut,
            addr = self.cfg.addr_control,
            data = 1
        )
        dut._log.info(msg = f"Engine start commanded! Running simulation for 50 cycles ...") #TODO FTH

        # Waits for Euoler integration cycles.
        await ClockCycles(
            signal = dut.clk,
            num_cycles = 50 
        )

        # Reads the data back over the bus.
        read_speed_value: int = await self._bus_read(
            dut = dut,
            addr = self.cfg.addr_speed
        )
        read_pressure_value: int = await self._bus_read(
            dut = dut,
            addr = self.cfg.addr_pressure
        )
        read_temperature_value: int = await self._bus_read(
            dut = dut,
            addr = self.cfg.addr_temperature
        )

        # Scales back the read-values to normal intervalls.
        speed_scaled: float = read_speed_value / (1 << 16)
        pressure_scaled: float = read_pressure_value / (1 << 16)
        temperature_scaled: float = read_temperature_value / (1 << 16)

        # Logs the results.
        dut._log.info(f"Read-Data: Speed: {speed_scaled:.2f}, Pressure: {pressure_scaled:.2f} kPa, Temperature: {temperature_scaled} *C")

        dut._log.info("Smoke test PASSED successfully!")

#* scripts/config_loader.py

#* ======= Libraries =======
# ------- Natives. -------
import tomllib
from typing import Any

from dataclasses import dataclass
from pathlib import Path

# ------- Custom. -------
from sim_model.quantize_floats import quantize_floats

#* ======= Data Class Initializations =======
@dataclass(frozen = True, slots = True)
class RepresentationConfig:
    int_bit_width: int
    fractional_bit_width: int

    def __post_init__(self) -> None:
        if self.int_bit_width <= 0:
            raise ValueError(
                f"int_bit_width must be positive, got {self.int_bit_width}"
            )

        if self.fractional_bit_width <= 0:
            raise ValueError(
                f"fractional_bit_width must be positive, got {self.fractional_bit_width}"
            )

        total_width = self.int_bit_width + self.fractional_bit_width
        if total_width != 32:
            raise ValueError(
                f"Total word length must equal 32 bits for AXI4-Lite CSR, got {total_width}"
            )

@dataclass(frozen = True, slots = True)
class SimulationConfig:
    simulation_step: float
    total_simulation_time: float

    def __post_init__(self) -> None:
        if self.simulation_step <= 0.0:
            raise ValueError(
                f"simulation_step (dt) must be strictly positive, got {self.simulation_step}"
            )

        if self.total_simulation_time <= self.simulation_step:
            raise ValueError(
                f"total_simulation_time ({self.total_simulation_time}) must be greater than step size ({self.simulation_step})"
            )

@dataclass(frozen = True, slots = True)
class AmbientConfig:
    ambient_pressure: float
    ambient_pressure_quantized: int
    ambient_temperature: float
    ambient_temperature_quantized: int

    def __post_init__(self) -> None:
        if self.ambient_pressure <= 0.0:
            raise ValueError(
                f"ambient_pressure must be physically positive, got {self.ambient_pressure} kPa"
            )

        if self.ambient_temperature <= -273.15:
            raise ValueError(
                f"ambient_temperature must be above absolute zero (-273.15 °C), got {self.ambient_temperature} °C"
            )

@dataclass(frozen = True, slots = True)
class InertiaConfig:
    rotor_inertial_time_const: float
    pre_calculated_rotor_inertial_time_const_quantized: int

    pressure_volume_time_const: float
    pre_calculated_pressure_volume_time_const_quantized: int

    thermal_time_const: float
    pre_calculated_thermal_time_const_quantized: int

    def __post_init__(self) -> None:
        if self.rotor_inertial_time_const <= 0.0:
            raise ValueError(
                f"rotor_inertial_time_const (tau_N) must be > 0.0, got {self.rotor_inertial_time_const}"
            )

        if self.pressure_volume_time_const <= 0.0:
            raise ValueError(
                f"pressure_volume_time_const (tau_P) must be > 0.0, got {self.pressure_volume_time_const}"
            )

        if self.thermal_time_const <= 0.0:
            raise ValueError(
                f"thermal_time_const (tau_T) must be > 0.0, got {self.thermal_time_const}"
            )

@dataclass(frozen = True, slots = True)
class GainConfig:
    speed_gain_coeff: float
    speed_gain_coeff_quantized: int

    compressor_pressure_gain: float
    compressor_pressure_gain_quantized: int

    combustion_heat_gain: float
    combustion_heat_gain_quantized: int

    mass_overflow_cooling_gain: float
    mass_overflow_cooling_gain_quantized: int

    def __post_init__(self) -> None:
        if self.speed_gain_coeff <= 0.0:
            raise ValueError(
                f"speed_gain_coeff must be > 0.0, got {self.speed_gain_coeff}"
            )

        if self.compressor_pressure_gain <= 0.0:
            raise ValueError(
                f"compressor_pressure_gain must be > 0.0, got {self.compressor_pressure_gain}"
            )

        if self.combustion_heat_gain <= 0.0:
            raise ValueError(
                f"combustion_heat_gain must be > 0.0, got {self.combustion_heat_gain}"
            )

        if self.mass_overflow_cooling_gain <= 0.0:
            raise ValueError(
                f"mass_overflow_cooling_gain must be > 0.0, got {self.mass_overflow_cooling_gain}"
            )

@dataclass(frozen = True, slots = True)
class LimitConfig:
    max_rotational_speed: float
    max_rotational_speed_quantized: int

    max_compressor_temperature: float
    max_compressor_temperature_quantized: int

    def __post_init__(self) -> None:
        if self.max_rotational_speed <= 0.0:
            raise ValueError(
                f"max_rotational_speed must be > 0.0, got {self.max_rotational_speed}"
            )

        if self.max_compressor_temperature <= 0.0:
            raise ValueError(
                f"max_compressor_temperature must be > 0.0, got {self.max_compressor_temperature}"
            )

@dataclass(frozen = True, slots = True)
class SynthesisConfig:
    synth_target_period: float
    sweep_low_period: float
    sweep_high_period: float

    def __post_init__(self) -> None:
        if self.synth_target_period <= 0.0:
            raise ValueError(
                f"synth_target_period must be > 0.0 ns, got {self.synth_target_period}"
            )

        if self.sweep_low_period <= 0.0:
            raise ValueError(
                f"sweep_low_period must be > 0.0 ns, got {self.sweep_low_period}"
            )

        if self.sweep_high_period <= self.sweep_low_period:
            raise ValueError(
                f"sweep_high_period ({self.sweep_high_period}) must be strictly greater than sweep_low_period ({self.sweep_low_period})"
            )

@dataclass(frozen = True, slots = True)
class RegisterConfig:
    addr_control: int
    addr_status: int
    addr_fuel_flow_cmd: int
    addr_speed: int
    addr_pressure: int
    addr_temperature: int
    addr_fault_injection: int

    def __post_init__(self) -> None:
        addresses: list[tuple[str, int]] = [
            ("addr_control", self.addr_control),
            ("addr_status", self.addr_status),
            ("addr_fuel_flow_cmd", self.addr_fuel_flow_cmd),
            ("addr_speed", self.addr_speed),
            ("addr_pressure", self.addr_pressure),
            ("addr_temperature", self.addr_temperature),
            ("addr_fault_injection", self.addr_fault_injection)
        ]

        # Enforces 32-bit (4-byte) boundary alignment.
        for name, addr in addresses:
            if addr < 0 or (addr % 4 != 0):
                raise ValueError(
                    f"Register {name} address (0x{addr:02X}) must be a positive 4-byte aligned offset"
                )

        # Enforces address uniqueness across CSR map.
        addr_values = [addr for _, addr in addresses]
        if len(addr_values) != len(set(addr_values)):
            raise ValueError(
                "Duplicate register addresses detected in RegisterConfig!"
            )

@dataclass(frozen = True, slots = True)
class TestbenchConfig:
    smoke_test_duration: float
    compressor_stall_test_duration: float
    max_thermal_threshold_cross_duration: float

    def __post_init__(self) -> None:
        if self.smoke_test_duration <= 0.0:
            raise ValueError(
                f"smoke_test_duration must be positive, got {self.smoke_test_duration}"
            )

        if self.compressor_stall_test_duration <= 0.0:
            raise ValueError(
                f"compressor_stall_test_duration must be positive, got {self.compressor_stall_test_duration}"
            )

        if self.max_thermal_threshold_cross_duration <= 0.0:
            raise ValueError(
                f"max_thermal_threshold_cross_duration must be positive, got {self.max_thermal_threshold_cross_duration}"
            )

@dataclass(frozen = True, slots = True)
class SystemConfig:
    representation: RepresentationConfig

    simulation: SimulationConfig

    ambient: AmbientConfig
    inertia: InertiaConfig
    gain: GainConfig
    limit: LimitConfig

    synthesis: SynthesisConfig
    register: RegisterConfig

    testbench: TestbenchConfig

    def __post_init__(self) -> None:
        # Cross-validation: Safety limit must exceed ambient condition.
        if (
            self.limit.max_compressor_temperature
            <= self.ambient.ambient_temperature
        ):
            raise ValueError(
                f"max_compressor_temperature ({self.limit.max_compressor_temperature} °C) "
                f"must be strictly greater than ambient_temperature ({self.ambient.ambient_temperature} °C)"
            )

#* ======= Config Loader Class =======
class ConfigLoader:
    def __init__(self) -> None:
        pass

    def load_config (
            self,
            config_file_path: Path
    ) -> SystemConfig:
        # ------- Config File Read and Validation. -------
        #? 'rb': Accepts the text streams as a binary file.
        # Reads the file.
        try:
            with open(
                config_file_path,
                mode = "rb"
            ) as file:
                cfg: dict[str, Any] = tomllib.load(file)
        except tomllib.TOMLDecodeError as err:
            print(f"Failed to parse config.toml syntax: {err}")
            raise

        # Defines some helper-parameters from the config file.
        INT_BIT_WIDTH: int = cfg["representation"]["int_bit_width"]
        FRACTIONAL_BIT_WIDTH: int = cfg["representation"]["fractional_bit_width"]

        SIMULATION_STEP: float = cfg["simulation"]["simulation_step"]

        # ------- Dataclass Initializations. -------
        # -> Representation.
        representation_cfg = RepresentationConfig(
            int_bit_width = cfg["representation"]["int_bit_width"],
            fractional_bit_width = cfg["representation"]["fractional_bit_width"]
        )

        # -> Simulation.
        simulation_cfg = SimulationConfig(
            simulation_step = cfg["simulation"]["simulation_step"],
            total_simulation_time = cfg["simulation"]["total_simulation_time"]
        )

        # -> Ambient.
        AMBIENT_PRESSURE: float = cfg["physics"]["ambient"]["ambient_pressure"]
        AMBIENT_PRESSURE_QUANTIZED: int = quantize_floats(
            val = AMBIENT_PRESSURE,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        AMBIENT_TEMPERATURE: float = cfg["physics"]["ambient"]["ambient_temperature"]
        AMBIENT_TEMPERATURE_QUANTIZED: int = quantize_floats(
            val = AMBIENT_TEMPERATURE,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )

        ambient_cfg = AmbientConfig(
            ambient_pressure = AMBIENT_PRESSURE,
            ambient_pressure_quantized = AMBIENT_PRESSURE_QUANTIZED,
            ambient_temperature = AMBIENT_TEMPERATURE,
            ambient_temperature_quantized = AMBIENT_TEMPERATURE_QUANTIZED
        )

        # -> Inertia.
        ROTOR_INERTIAL_TIME_CONST: float = cfg["physics"]["inertia"]["rotor_inertial_time_const"]
        PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST_QUANTIZED: int = quantize_floats(
            val = (SIMULATION_STEP / ROTOR_INERTIAL_TIME_CONST),
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        PRESSURE_VOLUME_TIME_CONST: float = cfg["physics"]["inertia"]["pressure_volume_time_const"]
        PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST_QUANTIZED: int = quantize_floats(
            val = (SIMULATION_STEP / PRESSURE_VOLUME_TIME_CONST),
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        THERMAL_TIME_CONST: float = cfg["physics"]["inertia"]["thermal_time_const"]
        PRE_CALCULATED_THERMAL_TIME_CONST_QUANTIZED: int = quantize_floats(
            val = (SIMULATION_STEP / THERMAL_TIME_CONST),
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )

        inertia_cfg = InertiaConfig(
            rotor_inertial_time_const = ROTOR_INERTIAL_TIME_CONST,
            pre_calculated_rotor_inertial_time_const_quantized = PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST_QUANTIZED,
            pressure_volume_time_const = PRESSURE_VOLUME_TIME_CONST,
            pre_calculated_pressure_volume_time_const_quantized = PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST_QUANTIZED,
            thermal_time_const = THERMAL_TIME_CONST,
            pre_calculated_thermal_time_const_quantized = PRE_CALCULATED_THERMAL_TIME_CONST_QUANTIZED
        )

        # -> Gain.
        SPEED_GAIN_COEFF: float = cfg["physics"]["gain"]["speed_gain_coeff"]
        SPEED_GAIN_COEFF_QUANTIZED: int = quantize_floats(
            val = SPEED_GAIN_COEFF,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        COMPRESSOR_PRESSURE_GAIN: float = cfg["physics"]["gain"]["compressor_pressure_gain"]
        COMPRESSOR_PRESSURE_GAIN_QUANTIZED: int = quantize_floats(
            val = COMPRESSOR_PRESSURE_GAIN,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        COMBUSTION_HEAT_GAIN: float = cfg["physics"]["gain"]["combustion_heat_gain"]
        COMBUSTION_HEAT_GAIN_QUANTIZED: int = quantize_floats(
            val = COMBUSTION_HEAT_GAIN,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        MASS_OVERFLOW_COOLING_GAIN: float = cfg["physics"]["gain"]["mass_overflow_cooling_gain"]
        MASS_OVERFLOW_COOLING_GAIN_QUANTIZED: int = quantize_floats(
            val = MASS_OVERFLOW_COOLING_GAIN,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )

        gain_cfg = GainConfig(
            speed_gain_coeff = SPEED_GAIN_COEFF,
            speed_gain_coeff_quantized = SPEED_GAIN_COEFF_QUANTIZED,
            compressor_pressure_gain = COMPRESSOR_PRESSURE_GAIN,
            compressor_pressure_gain_quantized = COMPRESSOR_PRESSURE_GAIN_QUANTIZED,
            combustion_heat_gain = COMBUSTION_HEAT_GAIN,
            combustion_heat_gain_quantized = COMBUSTION_HEAT_GAIN_QUANTIZED,
            mass_overflow_cooling_gain = MASS_OVERFLOW_COOLING_GAIN,
            mass_overflow_cooling_gain_quantized = MASS_OVERFLOW_COOLING_GAIN_QUANTIZED
        )

        # -> Limit.
        MAX_ROTATIONAL_SPEED: float = cfg["physics"]["limit"]["max_rotational_speed"]
        MAX_ROTATIONAL_SPEED_QUANTIZED: int = quantize_floats(
            val = MAX_ROTATIONAL_SPEED,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        MAX_COMPRESSOR_TEMPERATURE: float = cfg["physics"]["limit"]["max_compressor_temperature"]
        MAX_COMPRESSOR_TEMPERATURE_QUANTIZED: int = quantize_floats(
            val = MAX_COMPRESSOR_TEMPERATURE,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )

        limit_cfg = LimitConfig(
            max_rotational_speed = MAX_ROTATIONAL_SPEED,
            max_rotational_speed_quantized = MAX_ROTATIONAL_SPEED_QUANTIZED,
            max_compressor_temperature = MAX_COMPRESSOR_TEMPERATURE,
            max_compressor_temperature_quantized = MAX_COMPRESSOR_TEMPERATURE_QUANTIZED
        )

        # -> Synthesis.
        synthesis_cfg = SynthesisConfig(
            synth_target_period = cfg["hardware"]["synthesis"]["synth_target_period"],
            sweep_low_period = cfg["hardware"]["synthesis"]["sweep_low_period"],
            sweep_high_period = cfg["hardware"]["synthesis"]["sweep_high_period"]
        )
        # -> Register.
        register_cfg = RegisterConfig(
            addr_control = cfg["hardware"]["register"]["addr_control"],
            addr_status = cfg["hardware"]["register"]["addr_status"],
            addr_fuel_flow_cmd = cfg["hardware"]["register"]["addr_fuel_flow_cmd"],
            addr_speed = cfg["hardware"]["register"]["addr_speed"],
            addr_pressure = cfg["hardware"]["register"]["addr_pressure"],
            addr_temperature = cfg["hardware"]["register"]["addr_temperature"],
            addr_fault_injection = cfg["hardware"]["register"]["addr_fault_injection"]
        )

        # -> Testbench.
        testbench_cfg = TestbenchConfig(
            smoke_test_duration = cfg["testbench"]["smoke_test_duration"],
            compressor_stall_test_duration = cfg["testbench"]["compressor_stall_test_duration"],
            max_thermal_threshold_cross_duration = cfg["testbench"]["max_thermal_threshold_cross_duration"]
        )

        # -> System.
        cfg_dataclasses: dict[str, Any] = {
            "representation": representation_cfg,

            "simulation": simulation_cfg,

            "ambient": ambient_cfg,
            "inertia": inertia_cfg,
            "gain": gain_cfg,
            "limit": limit_cfg,

            "synthesis": synthesis_cfg,
            "register": register_cfg,

            "testbench": testbench_cfg
        }

        system_cfg = SystemConfig(**cfg_dataclasses)

        return system_cfg
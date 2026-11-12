
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
    """
    Configuration parameters defining fixed-point binary representation bit widths.

    Specifies integer and fractional bit boundaries for fixed-point quantization,
    ensuring standard 32-bit wordlength constraints compatible with the AXI4-Lite
    register bus interface.

    Attributes:
        int_bit_width (int): Number of bits allocated for the integer part, including sign.
        fractional_bit_width (int): Number of bits allocated for the fractional resolution.
    """
    int_bit_width: int
    fractional_bit_width: int

    def __post_init__(self) -> None:
        """
        Validates bit-width allocations and total word length constraints.

        Raises:
            ValueError: If int_bit_width or fractional_bit_width is non-positive,
                or if the total bit width does not equal 32 bits.

        Returns:
            None
        """
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
    """
    Configuration parameters governing the discrete numerical simulation duration and step size.

    Defines the discrete Euler solver integration interval and total simulation
    run time across both software reference models and hardware verification runs.

    Attributes:
        simulation_step (float): Discrete integration time step (dt) in seconds [s].
        total_simulation_time (float): Total physical duration of the simulation in seconds [s].
    """
    simulation_step: float
    total_simulation_time: float

    def __post_init__(self) -> None:
        """
        Validates numerical simulation time-step and total duration constraints.

        Raises:
            ValueError: If simulation_step is non-positive or if total_simulation_time
                is less than or equal to simulation_step.

        Returns:
            None
        """
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
    """
    Configuration parameters representing baseline atmospheric environmental conditions.

    Stores continuous physical constants and pre-quantized fixed-point representations
    for baseline ambient air pressure and air temperature.

    Attributes:
        ambient_pressure (float): Baseline atmospheric air pressure in kilopascals [kPa].
        ambient_pressure_quantized (int): Quantized ambient air pressure in raw fixed-point LSBs.
        ambient_temperature (float): Baseline ambient air temperature in degrees Celsius [°C].
        ambient_temperature_quantized (int): Quantized ambient temperature in raw fixed-point LSBs.
    """
    ambient_pressure: float
    ambient_pressure_quantized: int
    ambient_temperature: float
    ambient_temperature_quantized: int

    def __post_init__(self) -> None:
        """
        Validates physical plausibility of environmental atmospheric values.

        Raises:
            ValueError: If ambient_pressure is non-positive or if ambient_temperature
                is at or below absolute zero (-273.15 °C).

        Returns:
            None
        """
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
    """
    Configuration parameters governing physical inertia and aerodynamic time constants.

    Stores continuous time lag constants and pre-calculated division-free discrete
    integration factors (dt / tau) that eliminate hardware dividers in RTL integration stages.

    Attributes:
        rotor_inertial_time_const (float): Spool mechanical lag time constant (tau_N) in seconds [s].
        pre_calculated_rotor_inertial_time_const_quantized (int): Pre-calculated discrete rotor factor in LSBs.
        pressure_volume_time_const (float): Compressor pneumatic lag time constant (tau_P) in seconds [s].
        pre_calculated_pressure_volume_time_const_quantized (int): Pre-calculated discrete pressure factor in LSBs.
        thermal_time_const (float): Exhaust gas thermal lag time constant (tau_T) in seconds [s].
        pre_calculated_thermal_time_const_quantized (int): Pre-calculated discrete thermal factor in LSBs.
    """
    rotor_inertial_time_const: float
    pre_calculated_rotor_inertial_time_const_quantized: int

    pressure_volume_time_const: float
    pre_calculated_pressure_volume_time_const_quantized: int

    thermal_time_const: float
    pre_calculated_thermal_time_const_quantized: int

    def __post_init__(self) -> None:
        """
        Validates that all physical time constants are strictly positive.

        Raises:
            ValueError: If rotor_inertial_time_const, pressure_volume_time_const,
                or thermal_time_const is non-positive.

        Returns:
            None
        """
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
    """
    Configuration parameters defining physical thermodynamic transfer gains.

    Holds scaling coefficients and quantized fixed-point multipliers that convert
    actuator fuel flow and spool rotation into aerodynamic pressures and thermal outputs.

    Attributes:
        speed_gain_coeff (float): Speed gain coefficient (K_N) mapping fuel to target speed [% / (kg/h)].
        speed_gain_coeff_quantized (int): Quantized speed gain coefficient in raw LSBs.
        compressor_pressure_gain (float): Pressure gain (K_P) mapping speed squared to pressure [kPa / %²].
        compressor_pressure_gain_quantized (int): Quantized compressor pressure gain in raw LSBs.
        combustion_heat_gain (float): Combustion heat gain (K_heat) mapping fuel to heat [°C / (kg/h)].
        combustion_heat_gain_quantized (int): Quantized combustion heat gain in raw LSBs.
        mass_overflow_cooling_gain (float): Airflow cooling gain (K_cool) mapping speed to cooling [°C / %].
        mass_overflow_cooling_gain_quantized (int): Quantized airflow cooling gain in raw LSBs.
    """
    speed_gain_coeff: float
    speed_gain_coeff_quantized: int

    compressor_pressure_gain: float
    compressor_pressure_gain_quantized: int

    combustion_heat_gain: float
    combustion_heat_gain_quantized: int

    mass_overflow_cooling_gain: float
    mass_overflow_cooling_gain_quantized: int

    def __post_init__(self) -> None:
        """
        Validates that all physical thermodynamic gain coefficients are strictly positive.

        Raises:
            ValueError: If any gain coefficient is less than or equal to zero.

        Returns:
            None
        """
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
    """
    Configuration parameters establishing safety-critical trip boundaries and physical limits.

    Specifies operational ceilings for rotational speed and exhaust gas temperature,
    used to trigger automatic fuel cut-off and emergency states in the supervisory FSM.

    Attributes:
        max_rotational_speed (float): Maximum safe rotational spool speed limit in percent [%].
        max_rotational_speed_quantized (int): Quantized overspeed safety trip threshold in raw LSBs.
        max_compressor_temperature (float): Maximum safe exhaust gas temperature in degrees Celsius [°C].
        max_compressor_temperature_quantized (int): Quantized thermal meltdown threshold in raw LSBs.
    """
    max_rotational_speed: float
    max_rotational_speed_quantized: int

    max_compressor_temperature: float
    max_compressor_temperature_quantized: int

    def __post_init__(self) -> None:
        """
        Validates that structural and thermal safety thresholds are strictly positive.

        Raises:
            ValueError: If max_rotational_speed or max_compressor_temperature is non-positive.

        Returns:
            None
        """
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
    """
    Configuration parameters for AMD/Xilinx Vivado Out-of-Context synthesis and timing sweeps.

    Defines clock constraint periods and frequency interval boundaries used during
    automated Static Timing Analysis (STA) to evaluate timing closure and maximum achievable frequency.

    Attributes:
        synth_target_period (float): Default target clock period constraint in nanoseconds [ns].
        sweep_low_period (float): Lower bound period for binary search frequency sweeping in nanoseconds [ns].
        sweep_high_period (float): Upper bound period for binary search frequency sweeping in nanoseconds [ns].
    """
    synth_target_period: float
    sweep_low_period: float
    sweep_high_period: float

    def __post_init__(self) -> None:
        """
        Validates synthesis timing constraint boundaries and sweep interval consistency.

        Raises:
            ValueError: If any target or sweep period is non-positive, or if
                sweep_high_period is less than or equal to sweep_low_period.

        Returns:
            None
        """
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
    """
    Configuration parameters defining 32-bit AXI4-Lite memory-mapped register address offsets.

    Establishes the byte-level Control and Status Register (CSR) map for telemetry readouts,
    fuel command writes, FSM supervisor control, and fault-injection triggers.

    Attributes:
        addr_control (int): Byte address offset for the Engine Control Register (0x00).
        addr_status (int): Byte address offset for the Engine Safety Status Register (0x04).
        addr_fuel_flow_cmd (int): Byte address offset for Commanded Fuel Flow Register (0x08).
        addr_speed (int): Byte address offset for Rotational Speed Telemetry Register (0x0C).
        addr_pressure (int): Byte address offset for Compressor Pressure Telemetry Register (0x10).
        addr_temperature (int): Byte address offset for Exhaust Gas Temperature Register (0x14).
        addr_fault_injection (int): Byte address offset for Hardware Fault-Injection Register (0x18).
    """
    addr_control: int
    addr_status: int
    addr_fuel_flow_cmd: int
    addr_speed: int
    addr_pressure: int
    addr_temperature: int
    addr_fault_injection: int

    def __post_init__(self) -> None:
        """
        Validates 32-bit (4-byte) alignment and uniqueness across the AXI4-Lite register map.

        Raises:
            ValueError: If any register offset is negative, not aligned to a 4-byte boundary,
                or if duplicate address assignments are detected.

        Returns:
            None
        """
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
    """
    Configuration parameters governing duration limits for Cocotb hardware-in-the-loop tests.

    Defines execution intervals and timeout bounds for functional sanity checks,
    aerodynamic stall fault injection, and thermal runaway monitoring.

    Attributes:
        smoke_test_duration (float): Physical simulation run duration for smoke testing in seconds [s].
        compressor_stall_test_duration (float): Pre-fault run duration for stall injection in seconds [s].
        max_thermal_threshold_cross_duration (float): Maximum allowed timeout duration for thermal trip [s].
    """
    smoke_test_duration: float
    compressor_stall_test_duration: float
    max_thermal_threshold_cross_duration: float

    def __post_init__(self) -> None:
        """
        Validates that all testbench execution durations are strictly positive.

        Raises:
            ValueError: If smoke_test_duration, compressor_stall_test_duration, or
                max_thermal_threshold_cross_duration is non-positive.

        Returns:
            None
        """
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
    """
    Unified top-level system configuration container for the jet engine digital twin.

    Aggregates all validated subsystem dataclasses into a Central Single Source of
    Truth (CSST) coordinating mathematical models, hardware RTL synthesis, and verification.

    Attributes:
        representation (RepresentationConfig): Fixed-point arithmetic bit-width configurations.
        simulation (SimulationConfig): Discrete solver step size and total execution duration.
        ambient (AmbientConfig): Atmospheric air pressure and temperature baselines.
        inertia (InertiaConfig): Mechanical, pneumatic, and thermal time constants.
        gain (GainConfig): Aerodynamic, combustion, and cooling transfer gains.
        limit (LimitConfig): Overspeed and thermal meltdown safety trip thresholds.
        synthesis (SynthesisConfig): Vivado synthesis target clock constraints and sweep bounds.
        register (RegisterConfig): AXI4-Lite memory-mapped register address offsets.
        testbench (TestbenchConfig): Hardware co-simulation execution bounds and test timeouts.
    """
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
        """
        Validates cross-subsystem dependencies and physical consistency rules.

        Raises:
            ValueError: If the maximum compressor temperature limit does not strictly
                exceed the ambient environmental temperature.

        Returns:
            None
        """
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
    """
    Configuration parser, schema validator, and Central Single Source of Truth (CSST) factory.

    Parses the project-wide configuration file (config.toml), enforces strict schema key
    auditing to catch unmapped or misspelled parameters, computes pre-scaled fixed-point
    LSB representations, and populates strongly typed dataclasses for software and hardware pipelines.
    """
    def __init__(self) -> None:
        """
        Initializes the ConfigLoader instance.

        Returns:
            None
        """
        pass

    def _validate_config_keys(
                self,
                config: dict[str, Any]
        ) -> None:
            """
            Validates config.toml against predefined schemas to detect unmapped or extraneous keys.

            Performs root-table and parameter-level key comparisons using set differences.
            Prevents silent omission of misspelled, deprecated, or unexpected calibration parameters
            in compliance with DO-254 / ISO 26262 safety-critical validation requirements.

            Args:
                config (dict[str, Any]): Raw dictionary parsed directly from config.toml.

            Raises:
                ValueError: If unrecognized root tables or sub-table attributes are detected.

            Returns:
                None
            """
            # -> Schema Definitions.
            subclass_schemas: dict[str, set[str]] = {
                "representation": {
                    "int_bit_width",
                    "fractional_bit_width"
                },
                "simulation": {
                    "simulation_step",
                    "total_simulation_time"
                },
                "ambient": {
                    "ambient_pressure",
                    "ambient_temperature"
                },
                "inertia": {
                    "rotor_inertial_time_const",
                    "pressure_volume_time_const",
                    "thermal_time_const"
                },
                "gain": {
                    "speed_gain_coeff",
                    "compressor_pressure_gain",
                    "combustion_heat_gain",
                    "mass_overflow_cooling_gain"
                },
                "limit": {
                    "max_rotational_speed",
                    "max_compressor_temperature"
                },
                "synthesis": {
                    "synth_target_period",
                    "sweep_low_period",
                    "sweep_high_period"
                },
                "register": {
                    "addr_control",
                    "addr_status",
                    "addr_fuel_flow_cmd",
                    "addr_speed",
                    "addr_pressure",
                    "addr_temperature",
                    "addr_fault_injection"
                },
                "testbench": {
                    "smoke_test_duration",
                    "compressor_stall_test_duration",
                    "max_thermal_threshold_cross_duration"
                }
            }

            # Tracks all encountered diagnostic error messages.
            errors: list[str] = []

            # -> Root Table Validation.
            expected_root_tables: set[str] = set(subclass_schemas.keys())
            actual_root_tables: set[str] = set(config.keys())
            extra_root_tables: set[str] = actual_root_tables - expected_root_tables

            if extra_root_tables:
                errors.append(f"Root: Unrecognized tables: {sorted(extra_root_tables)}")

            # -> Sub-Table Parameter Validation
            for table_name, expected_keys in subclass_schemas.items():
                table_content = config.get(table_name)

                if isinstance(table_content, dict):
                    actual_keys: set[str] = set(table_content.keys())
                    extra_keys: set[str] = actual_keys - expected_keys

                    if extra_keys:
                        errors.append(f"[{table_name}]: Unrecognized attributes: {sorted(extra_keys)}")

            # Raises validation exception if unmapped keys were detected.
            if errors:
                formatted_errors: str = "\n  - ".join(errors)

                raise ValueError(
                    f"Schema validation failed! Unmapped attributes detected in config.toml:\n  - {formatted_errors}"
                )

    def load_config (
            self,
            config_file_path: Path
    ) -> SystemConfig:
        """
        Loads, validates, and transforms config.toml into a validated SystemConfig instance.

        Executes schema verification to ensure zero unmapped or misspelled parameters exist,
        extracts physical floating-point scalars, quantizes constants into bit-true Q16.16
        integers via quantize_floats(), and constructs immutable system dataclasses.

        Args:
            config_file_path (Path): Filesystem path to the root config.toml file.

        Raises:
            tomllib.TOMLDecodeError: If config.toml contains invalid TOML syntax.
            ValueError: If unmapped keys or invalid physical parameter ranges are detected.

        Returns:
            SystemConfig: Fully populated, strongly typed central configuration object.
        """
        
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

        # Validates the user-inputted parameters.
        self._validate_config_keys(config = cfg)

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
        AMBIENT_PRESSURE: float = cfg["ambient"]["ambient_pressure"]
        AMBIENT_PRESSURE_QUANTIZED: int = quantize_floats(
            val = AMBIENT_PRESSURE,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        AMBIENT_TEMPERATURE: float = cfg["ambient"]["ambient_temperature"]
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
        ROTOR_INERTIAL_TIME_CONST: float = cfg["inertia"]["rotor_inertial_time_const"]
        PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST_QUANTIZED: int = quantize_floats(
            val = (SIMULATION_STEP / ROTOR_INERTIAL_TIME_CONST),
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        PRESSURE_VOLUME_TIME_CONST: float = cfg["inertia"]["pressure_volume_time_const"]
        PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST_QUANTIZED: int = quantize_floats(
            val = (SIMULATION_STEP / PRESSURE_VOLUME_TIME_CONST),
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        THERMAL_TIME_CONST: float = cfg["inertia"]["thermal_time_const"]
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
        SPEED_GAIN_COEFF: float = cfg["gain"]["speed_gain_coeff"]
        SPEED_GAIN_COEFF_QUANTIZED: int = quantize_floats(
            val = SPEED_GAIN_COEFF,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        COMPRESSOR_PRESSURE_GAIN: float = cfg["gain"]["compressor_pressure_gain"]
        COMPRESSOR_PRESSURE_GAIN_QUANTIZED: int = quantize_floats(
            val = COMPRESSOR_PRESSURE_GAIN,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        COMBUSTION_HEAT_GAIN: float = cfg["gain"]["combustion_heat_gain"]
        COMBUSTION_HEAT_GAIN_QUANTIZED: int = quantize_floats(
            val = COMBUSTION_HEAT_GAIN,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        MASS_OVERFLOW_COOLING_GAIN: float = cfg["gain"]["mass_overflow_cooling_gain"]
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
        MAX_ROTATIONAL_SPEED: float = cfg["limit"]["max_rotational_speed"]
        MAX_ROTATIONAL_SPEED_QUANTIZED: int = quantize_floats(
            val = MAX_ROTATIONAL_SPEED,
            int_bit_width = INT_BIT_WIDTH,
            fractional_bit_width = FRACTIONAL_BIT_WIDTH,
            signed = True
        )
        MAX_COMPRESSOR_TEMPERATURE: float = cfg["limit"]["max_compressor_temperature"]
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
            synth_target_period = cfg["synthesis"]["synth_target_period"],
            sweep_low_period = cfg["synthesis"]["sweep_low_period"],
            sweep_high_period = cfg["synthesis"]["sweep_high_period"]
        )
        # -> Register.
        register_cfg = RegisterConfig(
            addr_control = cfg["register"]["addr_control"],
            addr_status = cfg["register"]["addr_status"],
            addr_fuel_flow_cmd = cfg["register"]["addr_fuel_flow_cmd"],
            addr_speed = cfg["register"]["addr_speed"],
            addr_pressure = cfg["register"]["addr_pressure"],
            addr_temperature = cfg["register"]["addr_temperature"],
            addr_fault_injection = cfg["register"]["addr_fault_injection"]
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
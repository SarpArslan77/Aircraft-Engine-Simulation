
#* aircraft_engine_simulator_fixed_point.py

#TODOS
# 1) For all the mathematical equations, write them as comments as well.

#* ======= Libraries =======
# ------- Natives. -------
from dataclasses import dataclass
from decimal import (
    Decimal,
    DecimalTuple
)

# ------- Externals. -------
import numpy as np
from numpy import (
    float64,
    int64
)
from numpy.typing import NDArray
import pandas as pd
from pandas import DataFrame
from pathlib import Path

# ------- Custom. -------
from quantize_floats import quantize_floats

#* ======= Aircraft Engine Simulator's (Fixed Point Type) Config Dataclass =======
@dataclass(frozen = True)
class ConfigAircraftEngineSimulatorFixedPoint:
    """
    Configuration parameters for the discrete fixed-point engine simulator.

    All physical floating-point quantities are pre-scaled and quantized into raw signed integers
    based on the specified integer and fractional bit widths.

    Attributes:
        int_bit_width (float): Bit width allocated for the integer portion of the representation (including sign bit).
        fractional_bit_width (float): Bit width allocated for the fractional portion.
        simulation_step (int): Discrete integration time step (dt) used in the Euler solver [s].
        total_simulation_time (int): Total physical duration of the simulation run [s].
        ambient_pressure_quantized (int): Quantized baseline atmospheric air pressure (P_amb) [Raw LSBs].
        ambient_temperature_quantized (int): Quantized baseline atmospheric air temperature (T_amb) [Raw LSBs].
        rotor_inertial_time_const_quantized (int): Quantized rotor mechanical lag time constant (tau_N) [Raw LSBs].
        pressure_volume_time_const_quantized (int): Quantized internal air pressure lag time constant (tau_P) [Raw LSBs].
        thermal_time_const_quantized (int): Quantized exhaust gas temperature lag time constant (tau_T) [Raw LSBs].
        speed_gain_coeff_quantized (int): Quantized speed gain coefficient (K_N) mapping fuel to target speed [Raw LSBs].
        compressor_pressure_gain_quantized (int): Quantized pressure gain coefficient (K_P) mapping speed squared to pressure [Raw LSBs].
        combustion_heat_gain_quantized (int): Quantized combustion thermal coefficient (K_heat) mapping fuel to heat [Raw LSBs].
        mass_overflow_cooling_gain_quantized (int): Quantized airflow cooling coefficient (K_cool) mapping speed to cooling [Raw LSBs].
        max_rotational_speed_quantized (int): Quantized safety limit for engine overspeed failures [Raw LSBs].
        max_compressor_temperature_quantized (int): Quantized safety limit for engine thermal meltdown failures [Raw LSBs].
    """
    # ------- Data Representation. -------
    int_bit_width: float
    fractional_bit_width: float

    # ------- Simulation. -------
    simulation_step: int
    total_simulation_time: int

    # ------- Ambient Conditions. -------
    ambient_pressure_quantized: int
    ambient_temperature_quantized: int

    # ------- Time Constants (Inertia). -------
    rotor_inertial_time_const_quantized: int
    pressure_volume_time_const_quantized: int
    thermal_time_const_quantized: int

    # ------- Gains. -------
    speed_gain_coeff_quantized: int
    compressor_pressure_gain_quantized: int
    combustion_heat_gain_quantized: int
    mass_overflow_cooling_gain_quantized: int

    # ------- Engine Limits. -------
    max_rotational_speed_quantized: int
    max_compressor_temperature_quantized: int

    # ------- Path. -------
    software_results_file_path: Path

#* ======= Aircraft Engine Simulator =======
quantized_values_type = tuple[int, int, int]
histories_type = tuple[NDArray[int64], NDArray, NDArray[int64], NDArray[int64], NDArray[int64], NDArray[int64]]

class AircraftEngineSimulatorFixedPoint:
    def __init__(
            self,
            config_aircraft_engine_simulator_fixed_point: ConfigAircraftEngineSimulatorFixedPoint
    ) -> None:
        """
        Initializes the AircraftEngineSimulatorFixedPoint with the specified configuration.

        Args:
            config_aircraft_engine_simulator_fixed_point (ConfigAircraftEngineSimulatorFixedPoint): 
                The configuration dataclass holding fixed-point representation parameters, 
                quantized environment conditions, and simulation parameters.
        """
        self._cfg: ConfigAircraftEngineSimulatorFixedPoint = config_aircraft_engine_simulator_fixed_point

    def _fetch_current_fuel_flow(
            self,
            k: float
    ) -> int:
        """
        Determines and returns the quantized fuel flow rate based on the current simulation time.

        The fuel flow rate profile represents a typical operational cycle:
        - Idle: 10 kg/h for t < 2.0 s
        - Rapid Acceleration (Throttle Slam): 90 kg/h for 2.0 s <= t < 18.0 s
        - Deceleration (Throttle Chop): 10 kg/h for t >= 18.0 s

        The float values are quantized using the configured bit width.

        Args:
            k (float): The current simulation time in seconds.

        Returns:
            int: The quantized fuel flow rate (W_f) in fixed-point representation.
        """

        # Idle fuel flow.
        if k < 2.0:
            fuel_flow_float: int = 10
        # Throttle slam / rapic acceleration.
        elif k < 18.0:
            fuel_flow_float: int = 90
        # Throttle chop / deceleration.
        else:
            fuel_flow_float: int = 10

        # Quantizes the fuel flow.
        return quantize_floats(
            val = fuel_flow_float,
            int_bit_width = self._cfg.int_bit_width,
            fractional_bit_width = self._cfg.fractional_bit_width,
            signed = True
        )

    def _calculate_target_values(
            self,
            current_fuel_flow: int,
            current_rotational_speed: int,
            gain_constants: tuple[int, int, int, int]
    ) -> quantized_values_type:
        """
        Calculates the quantized target values for engine rotational speed, compressor 
        pressure, and exhaust gas temperature using fixed-point arithmetic.

        Mathematical Equations:
        1) Target Rotational Speed:
           N_target = (K_N * W_f) >> f_width
        2) Target Compressor Pressure:
           P_target = P_amb + (K_P * (N^2 >> f_width)) >> f_width
        3) Target Exhaust Gas Temperature:
           T_target = T_amb + ((K_heat * W_f) >> f_width) - ((K_cool * N) >> f_width)

        Args:
            current_fuel_flow (int): Current quantized fuel flow rate (W_f).
            current_speed (int): Current quantized rotational speed (N).
            gain_constants (tuple[int, int, int, int]): A tuple containing:
                - speed_gain_coefficient (int): K_N (Speed Gain Coefficient)
                - compressor_pressure_gain (int): K_P (Compressor Pressure Gain)
                - combustion_heat_gain (int): K_heat (Combustion Heat Gain)
                - mass_overflow_cooling_gain (int): K_cool (Mass-Airflow Cooling Gain)

        Returns:
            quantized_values_type: A tuple containing:
                - target_rotational_speed (int): Target speed (N_target).
                - target_compressor_pressure (int): Target pressure (P_target).
                - target_exhaust_gas_temperature (int): Target temperature (T_target).
        """
        # Unpacks the gain constants.
        speed_gain_coefficient, compressor_pressure_gain, combustion_heat_gain, mass_overflow_cooling_gain = gain_constants

        f_width: int = self._cfg.fractional_bit_width

        # ------- Calculates target values. -------
        # All values has to be shifted to the right 'fractional_bit_width' in order to match the original bit widths.
        # Rotational Speed.
        target_rotational_speed: int = (speed_gain_coefficient * current_fuel_flow) >> f_width

        # Compressor Pressure.
        target_compressor_pressure: int = self._cfg.ambient_pressure_quantized + ((compressor_pressure_gain * (((current_rotational_speed)**2) >> f_width)) >> f_width) 

        # Exhaust Gas Temperature.
        target_exhaust_gas_temperature: int = self._cfg.ambient_temperature_quantized + ((combustion_heat_gain * current_fuel_flow) >> f_width) - ((mass_overflow_cooling_gain * current_rotational_speed) >> f_width)

        return (target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature)

    def _calculate_derivatives(
            self,
            current_values: quantized_values_type,
            target_values: quantized_values_type
    ) -> quantized_values_type:
        """
        Calculates the quantized intermediate derivative terms for the integration step.
        To avoid costly divisions at runtime, division constants are pre-scaled and optimized.

        Mathematical Equations:
        1) Pre-calculated Constants (scaled by 2^(2 * f_width) to preserve precision):
           pre_const = round((dt / tau) * 2^(2 * f_width))
        2) Intermediate Scaled Derivatives:
           d_N = pre_const_N * (N_target - N)
           d_P = pre_const_P * (P_target - P)
           d_T = pre_const_T * (T_target - T)

        Args:
            current_values (quantized_values_type): A tuple containing:
                - current_rotational_speed (int): N[k]
                - current_compressor_pressure (int): P[k]
                - current_exhaust_gas_temperature (int): T[k]
            target_values (quantized_values_type): A tuple containing:
                - target_rotational_speed (int): N_target[k]
                - target_compressor_pressure (int): P_target[k]
                - target_exhaust_gas_temperature (int): T_target[k]

        Returns:
            quantized_values_type: A tuple containing the intermediate scaled derivative values:
                - d_rotational_speed (int): Scaled change in rotational speed.
                - d_compressor_pressure (int): Scaled change in compressor pressure.
                - d_exhaust_gas_temperature (int): Scaled change in exhaust gas temperature.
        """
        # Unpacks the parameters.
        current_rotational_speed, current_compressor_pressure, current_exhaust_gas_temperature = current_values
        target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature = target_values

        # Optimizes division constants away.
        pre_calculated_rotor_inertial_time_const_quantized: int = round((self._cfg.simulation_step / self._cfg.rotor_inertial_time_const_quantized) * (1 << (2 * self._cfg.fractional_bit_width)))
        pre_calculated_pressure_volume_time_const_quantized: int = round((self._cfg.simulation_step / self._cfg.pressure_volume_time_const_quantized) * (1 << (2 * self._cfg.fractional_bit_width)))
        pre_calculated_thermal_time_const_quantized: int = round((self._cfg.simulation_step / self._cfg.thermal_time_const_quantized) * (1 << (2 * self._cfg.fractional_bit_width)))

        # ------- Calculates the derivatives. -------
        # Rotational Speed.
        d_rotational_speed: int = pre_calculated_rotor_inertial_time_const_quantized * (target_rotational_speed - current_rotational_speed)

        # Compressor Pressure.
        d_compressor_pressure: int = pre_calculated_pressure_volume_time_const_quantized * (target_compressor_pressure - current_compressor_pressure)

        # Exhaust Gas Temperature.
        d_exhaust_gas_temperature: int = pre_calculated_thermal_time_const_quantized * (target_exhaust_gas_temperature - current_exhaust_gas_temperature)

        return (d_rotational_speed, d_compressor_pressure, d_exhaust_gas_temperature)

    def _calculate_next_step(
            self,
            current_values: quantized_values_type,
            derivative_values: quantized_values_type
    ) -> quantized_values_type:
        """
        Computes the state values for the next simulation step using Euler integration
        and shifting the pre-scaled derivative terms back to the correct fractional width.

        Mathematical Equations (Euler Integration):
        1) Next Rotational Speed:
           N[k+1] = N[k] + (d_N >> f_width)
        2) Next Compressor Pressure:
           P[k+1] = P[k] + (d_P >> f_width)
        3) Next Exhaust Gas Temperature:
           T[k+1] = T[k] + (d_T >> f_width)

        Args:
            current_values (quantized_values_type): A tuple containing:
                - current_rotational_speed (int): N[k]
                - current_compressor_pressure (int): P[k]
                - current_exhaust_gas_temperature (int): T[k]
            derivative_values (quantized_values_type): A tuple containing:
                - d_rotational_speed (int): Pre-scaled derivative term for speed.
                - d_compressor_pressure (int): Pre-scaled derivative term for pressure.
                - d_exhaust_gas_temperature (int): Pre-scaled derivative term for temperature.

        Returns:
            quantized_values_type: A tuple containing the updated states for the next step:
                - next_rotational_speed (int): N[k+1]
                - next_compressor_pressure (int): P[k+1]
                - next_exhaust_gas_temperature (int): T[k+1]
        """
        # Unpacks the parameters.
        current_rotational_speed, current_compressor_pressure, current_exhaust_gas_temperature = current_values
        d_rotational_speed, d_compressor_pressure, d_exhaust_gas_temperature = derivative_values

        f_bit: int = self._cfg.fractional_bit_width

        # Uses the Euler equation to compute the values for the next step.
        next_rotational_speed: int = current_rotational_speed + (d_rotational_speed >> f_bit)

        next_compressor_pressure: int = current_compressor_pressure + (d_compressor_pressure >> f_bit)

        next_exhaust_gas_temperature: int = current_exhaust_gas_temperature + (d_exhaust_gas_temperature >> f_bit)

        return (next_rotational_speed, next_compressor_pressure, next_exhaust_gas_temperature)

    def _export_histories(
            self,
            histories: histories_type
    ) -> None:
        """
        Exports the complete simulation state histories and input telemetry to a CSV file.

        The generated dataset serves as a golden software reference for verification 
        and comparison against fixed-point hardware/FPGA simulation outputs.

        Args:
            histories (histories_type): A tuple containing the simulation arrays:
                - fuel_flow_history (NDArray[int64]): Quantized fuel flow rate (W_f) over time.
                - speed_history (NDArray[int64]): Quantized engine rotational speed (N) over time.
                - pressure_history (NDArray[int64]): Quantized compressor pressure (P) over time.
                - temperature_history (NDArray[int64]): Quantized exhaust gas temperature (T) over time.
                - is_engine_broken_history (NDArray[int64]): Binary structural failure flags (1 = broken, 0 = operational) over time.
                - time_history (NDArray[float64]): Physical simulation time steps in seconds (t).

        Returns:
            None
        """
        # Unpacks the histories.
        fuel_flow_history, speed_history, pressure_history, temperature_history, is_engine_broken_history, time_history = histories

        # Declares a pandas dataframe.
        df = DataFrame(
            data = {
                "fuel_flow": fuel_flow_history,
                "speed": speed_history,
                "pressure": pressure_history,
                "temperature": temperature_history,
                "is_engine_broken": is_engine_broken_history,
                "time": time_history
            }
        )

        software_results_file_name: Path = self._cfg.software_results_file_path / "software_results.csv"

        # Exports the dataframe as a csv file.
        df.to_csv(
            software_results_file_name,
            index = False
        )

    def run_simulation(
            self,
            initial_conditions: tuple[int, int, int]
    ) -> histories_type:
        """
        Executes the discrete-time fixed-point engine simulation loop.

        At each discrete time step, the solver:
        1. Evaluates fuel flow profile based on simulation time.
        2. If structural failure has occurred, simulates engine shutdown (fuel cut-off and zeroed gains).
        3. Evaluates target rotational speed, compressor pressure, and exhaust gas temperature.
        4. Computes state derivatives using optimized, division-free fixed-point arithmetic.
        5. Advances system states using forward Euler integration.
        6. Enforces physical safeguard clamping to avoid negative speeds or sub-ambient values.
        7. Checks structural failure boundaries (overspeed and thermal meltdown).
        8. Exports final history data to CSV for hardware co-verification.

        Mathematical Equations & Physical Constraints:
        1) Total Iteration Count:
        total_steps = ceil(total_simulation_time / simulation_step)
        2) Simulation Time Step:
        k = i * simulation_step
        3) Safeguard Lower Clamping:
        N_next = max(0, N_next)
        P_next = max(P_amb_quantized, P_next)
        T_next = max(T_amb_quantized, T_next)
        4) Structural Failure Condition:
        is_broken = (N[k] > N_max_quantized) or (T[k] > T_max_quantized)
        5) Post-Failure Engine Cut-off Behavior:
        If is_broken == True:
            W_f = 0
            K_N = 0,  K_P = 0,  K_heat = 0,  K_cool = 0

        Args:
            initial_conditions (tuple[int, int, int]): Initial state values at t = 0:
                - initial_speed (int): Quantized initial rotational speed (N[0]).
                - initial_pressure (int): Quantized initial compressor pressure (P[0]).
                - initial_temperature (int): Quantized initial exhaust gas temperature (T[0]).

        Returns:
            histories_type: A tuple containing 6 NumPy arrays of length (total_steps + 1):
                - fuel_flow_history (NDArray[int64]): Quantized fuel flow history (W_f).
                - speed_history (NDArray[int64]): Quantized rotational speed history (N).
                - pressure_history (NDArray[int64]): Quantized compressor pressure history (P).
                - temperature_history (NDArray[int64]): Quantized exhaust gas temperature history (T).
                - is_engine_broken_history (NDArray[int64]): Engine structural health flag history.
                - time_history (NDArray[float64]): Physical simulation time steps in seconds (t).
        """
        # Unpacks the initial conditions.
        initial_speed, initial_pressure, initial_temperature = initial_conditions

        # Calculates the total number of iterations needed.
        total_steps = int(
            np.ceil(self._cfg.total_simulation_time / self._cfg.simulation_step)
        )

        # Calculates to how many digits the time history should be rounded to.
        simulation_step_str = str(self._cfg.simulation_step)
        #? Decimal(): Class for exact base-10 arithmetic, rather than base-2 binary math.
        simulation_step_decimal = Decimal(value = simulation_step_str)
        #? .as_tuple(): Decomposes a Decimal object to its mathematical parts.
        #   f.e. '0.001' -> DecimalTuple(sign = 0, digits = (1,), exponent = -3)
        simulation_step_decimal_tuple: DecimalTuple = simulation_step_decimal.as_tuple()
        #?  .exponent: Extracts jus the exponent integer of a DecimalTuple.
        simulation_step_decimal_exponent: int = simulation_step_decimal_tuple.exponent
        
        time_history_rounding_decimals: int = max(0, -simulation_step_decimal_exponent)

        # Populates the time history as it is deterministic.
        time_history: NDArray[float64] = np.linspace(
            start = 0.0,
            stop = self._cfg.total_simulation_time,
            num = total_steps + 1,
            dtype = float64
        ).round(decimals = time_history_rounding_decimals) #TODO FTH

        # Creates empty data structures.
        fuel_flow_history: NDArray[int64] = np.empty(
            total_steps + 1,
            int64
        )

        speed_history: NDArray[int64] = np.empty(
            total_steps + 1,
            int64
        )
        speed_history[0]= initial_speed

        pressure_history: NDArray[int64] = np.empty(
            total_steps + 1,
            int64
        )
        pressure_history[0]= initial_pressure

        temperature_history: NDArray[int64] = np.empty(
            total_steps + 1,
            int64
        )
        temperature_history[0]= initial_temperature

        is_engine_broken_history: NDArray[int64] = np.empty(
            total_steps + 1,
            int64
        )

        # ------- Simulation Loop. -------
        is_engine_broken: bool = False
        # Defines local variables for the gains, so they can be modified if the engine breaks.
        speed_gain_coeff: int = self._cfg.speed_gain_coeff_quantized
        compressor_pressure_gain: int = self._cfg.compressor_pressure_gain_quantized
        combustion_heat_gain: int = self._cfg.combustion_heat_gain_quantized
        mass_overflow_cooling_gain: int = self._cfg.mass_overflow_cooling_gain_quantized

        for i in range(0, total_steps):
            # Calculates the current physical simulation time.
            k: float = i * self._cfg.simulation_step

            # Modifies the system behaviour, IF engine is broken.
            if is_engine_broken:
                # Simulates a cut-off.
                current_fuel_flow: int = 0
            
                speed_gain_coeff = 0
                compressor_pressure_gain = 0
                combustion_heat_gain = 0
                mass_overflow_cooling_gain = 0
            
            else:
                # Fetches the inputs.
                current_fuel_flow: int = self._fetch_current_fuel_flow(k = k)

            is_engine_broken_history[i] = is_engine_broken
            
            fuel_flow_history[i] = current_fuel_flow

            # Retrieves the current values.
            current_speed = speed_history[i]
            current_pressure = pressure_history[i]
            current_temperature = temperature_history[i]

            # Calculates the target values.
            target_speed, target_pressure, target_temperature = self._calculate_target_values(
                current_fuel_flow = current_fuel_flow,
                current_rotational_speed = current_speed,
                gain_constants = (speed_gain_coeff, compressor_pressure_gain, combustion_heat_gain, mass_overflow_cooling_gain)
            )

            # Calculates the derivatives.
            current_values: quantized_values_type = (current_speed, current_pressure, current_temperature)
            
            d_speed, d_pressure, d_temperature = self._calculate_derivatives(
                current_values = current_values,
                target_values = (target_speed, target_pressure, target_temperature)
            )

            # Calculates the next step values.
            next_speed, next_pressure, next_temperature = self._calculate_next_step(
                current_values = current_values,
                derivative_values = (d_speed, d_pressure, d_temperature)
            )

            # ------- Controls the next values. -------
            # Clamps the results to minimum safeguards.
            if (next_speed < 0):
                next_speed = 0
            
            if (next_pressure < self._cfg.ambient_pressure_quantized):
                next_pressure = self._cfg.ambient_pressure_quantized
            
            if (next_temperature < self._cfg.ambient_temperature_quantized):
                next_temperature = self._cfg.ambient_temperature_quantized
            
            # Monitors for maximum limit breaches.
            if (current_speed > self._cfg.max_rotational_speed_quantized) or \
                (current_temperature > self._cfg.max_compressor_temperature_quantized):
                is_engine_broken = True
            
            speed_history[i+1] = next_speed
            pressure_history[i+1] = next_pressure
            temperature_history[i+1] = next_temperature
            
        # Adds the last state of fuel flow and engine state to the history.
        last_fuel_flow: int = self._fetch_current_fuel_flow(k = (total_steps * self._cfg.simulation_step))
        
        fuel_flow_history[total_steps] = last_fuel_flow

        is_engine_broken_history[total_steps] = is_engine_broken

        # Packs all the histories in a single tuple.
        histories: histories_type = (fuel_flow_history, speed_history, pressure_history, temperature_history, is_engine_broken_history, time_history)

        # Exports the input and output histories, so the data can be used as a golden reference, when compared to hardware outputs.
        self._export_histories(histories = histories)
        
        return histories
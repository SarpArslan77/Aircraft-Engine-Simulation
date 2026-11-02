
#* sim_model/aircraft_engine_simulator_floating.py

#? In order to calculate how the engine changes over time in the loop,
#?   these discrete equations must be evaluated at every time step 'k'.

#* A) Rotational Speed 'N': Engine speed (normalized from 0% to 100%).
# 1) Target Speed: N_target[k] = K_N * W_f[k].
#   where as: K_N: Speed Gain Coefficient & W_f: Fuel Flow Rate.
# 2) Rate of Change: (dN/dt)[k] = (1/tau_N) * (N_target[k] - N[k]).
#   tau_N: Rotor Inertial Time Constant.
# 3) Next State (Integration): N[k+1] = N[k] + ((dN/dt)[k] * delta(t)).

#* B) Compressor Pressure 'P': Pressure inside the engine (in kPa).
# 1) P_target[k] = P_amb + (K_P * (N[k])^2).
#   P_amb: Ambient Atmospheric Pressure & K_P: Compressor Pressure Gain.
# 2) (dP/dt)[k] = 1/(tau_P) * (P_target[k] - P[k]).
#   tau_P: Pressure Volume Time Constant.
# 3) P[k+1] = P[k] + ((dP/dt)[k] * delta(t)).

#* C) Exhaust Gas Temperature 'T': Thermal output (in *C).
# 1) T_target[k] = T_amb + (K_heat * W_f[k]) - (K_cool * N[k]).
#   T_amb: Ambient Air Temperature & K_heat: Combustion Heat Gain & K_cool: Mass-Airflow Cooling Gain.
# 2) (dT/dt)[k] = 1/(tau_T) * (T_target[k] - T[k]).
#   tau_T: Thermal Time Constant.
# 3) T[k+1] = T[k] + ((dT/dt)[k] * delta(t)).

#? These suggested coefficients yields a stable, physically balanced and
#?   highly visible transient behaviour when plotted:

# 1) Simulation Step 'delta(t)' = 1 ms.
# 2) Ambient Conditions: P_amb = 101.3 kPa & T_amb = 15.0 *C.
# 3) Time Constants (Intertia):
#   i) tau_N = 1.5 s (Heavy metal turbine rotor accelerates slowly).
#   ii) tau_P = 0.15 s (Air pressure reacts almost instantly).
#   iii) tau_T = 0.8 s (Thermal mass changes at a medium rate).
# 4) Gains:
#   i) K_N = 1.0 (So 100% fuel results in 100% engine speed).
#   ii) K_P = 0.015 (At 100% speed, 100^2 * 0.015 = 150 kPa over ambient pressure).
#   iii) K_heat = 15.0 (Burning max fuel adds up to +1500 *C of raw heat).
#   iv) K_cool = 6.0 (At 100% compressor speed, airflow cooling subtracts up to -600 *C).

#* ======= Libraries =======
# ------- Natives. -------
from dataclasses import dataclass

# ------- Externals. -------
import numpy as np
from numpy import float64
from numpy.typing import NDArray


#* ======= Aircraft Engine Simulator's (Floating Type) Config Dataclass =======
@dataclass(frozen = True)
class ConfigAircraftEngineSimulatorFloating:
    """
    Configuration parameters for the continuous-time floating-point engine simulator.

    Attributes:
        simulation_step (float): Discrete integration time step (dt) used in the Euler solver [s].
        total_simulation_time (float): Total physical duration of the simulation run [s].
        ambient_pressure (float): Baseline atmospheric air pressure (P_amb) [kPa].
        ambient_temperature (float): Baseline atmospheric air temperature (T_amb) [°C].
        rotor_inertial_time_const (float): Rotor mechanical lag time constant (tau_N) [s].
        pressure_volume_time_const (float): Internal air pressure lag time constant (tau_P) [s].
        thermal_time_const (float): Exhaust gas temperature lag time constant (tau_T) [s].
        speed_gain_coeff (float): Speed gain coefficient (K_N) mapping fuel flow rate to target speed [% / (kg/h)].
        compressor_pressure_gain (float): Pressure gain coefficient (K_P) mapping rotational speed squared to pressure [kPa / %^2].
        combustion_heat_gain (float): Combustion thermal coefficient (K_heat) mapping fuel flow to raw heat [°C / (kg/h)].
        mass_overflow_cooling_gain (float): Airflow cooling coefficient (K_cool) mapping speed to cooling effect [°C / %].
        max_rotational_speed (float): Maximum threshold for engine speed to avoid structural overspeed failure [%].
        max_compressor_temperature (float): Maximum threshold for engine temperature to avoid thermal meltdown [°C].
    """
    # ------- Simulation. -------
    simulation_step: float
    total_simulation_time: float

    # ------- Ambient Conditions. -------
    ambient_pressure: float
    ambient_temperature: float

    # ------- Time Constants (Inertia). -------
    rotor_inertial_time_const: float
    pressure_volume_time_const: float
    thermal_time_const: float

    # ------- Gains. -------
    speed_gain_coeff: float
    compressor_pressure_gain: float
    combustion_heat_gain: float
    mass_overflow_cooling_gain: float

    # ------- Engine Limits. -------
    max_rotational_speed: float
    max_compressor_temperature: float

#* ======= Aircraft Engine Simulator =======
values_type = tuple[float, float, float]

class AircraftEngineSimulatorFloating:
    """
    Continuous floating-point reference simulator for a single-spool turbojet engine.

    Solves non-linear continuous thermodynamic and mechanical differential equations across
    discrete time steps using 64-bit floating-point arithmetic and first-order forward Euler
    integration. Acts as the golden mathematical baseline to quantify fixed-point quantization
    noise, Root Mean Square Error (RMSE), and Signal-to-Quantization-Noise Ratio (SQNR).
    """
    def __init__(
            self,
            config_aircraft_engine_simulator_floating: ConfigAircraftEngineSimulatorFloating
    ) -> None:
        """
        Initializes the AircraftEngineSimulatorFloating with continuous system parameters.

        Args:
            config_aircraft_engine_simulator_floating (ConfigAircraftEngineSimulatorFloating):
                Configuration dataclass holding continuous physical constants, ambient conditions,
                aerodynamic and mechanical time constants (tau), physical gains, and safety bounds.

        Returns:
            None
        """
        self._cfg: ConfigAircraftEngineSimulatorFloating = config_aircraft_engine_simulator_floating
        
    def _fetch_current_fuel_flow(
            self,
            k: float
    ) -> float:
        """
        Evaluates the physical commanded fuel flow rate based on simulation time.

        Maps a continuous operational engine mission schedule:
        - Idle: 10.0 kg/h for t < 2.0 s
        - Throttle Slam (Rapid Acceleration): 90.0 kg/h for 2.0 s <= t < 18.0 s
        - Throttle Chop (Deceleration): 10.0 kg/h for t >= 18.0 s

        Args:
            k (float): Current physical simulation time in seconds.

        Returns:
            float: Commanded fuel flow rate (W_f) in engineering units [kg/h].
        """
        fuel_flow: float | None = None

        # Idle fuel flow.
        if (k == 0.0):
            fuel_flow = 10.0
        if (0.0 < k < 2.0):
            fuel_flow = 10.0

        # Throttle slam / rapic acceleration.
        elif (k == 2.0) or (2.0 < k < 18.0):
            fuel_flow = 90.0

        # Throttle chop / deceleration.
        elif (k == 18.0) or (18.0 < k < self._cfg.total_simulation_time) or (k == self._cfg.total_simulation_time):
            fuel_flow = 10.0

        return fuel_flow

    def _calculate_target_values(
            self,
            current_fuel_flow: float,
            current_speed: float,
            gain_constants: tuple[float, float, float, float]
    ) -> values_type:
        """
        Calculates the continuous target steady-state values for all engine states.

        Mathematical Formulations:
        1. Target Rotational Speed:
        N_target = K_N * W_f
        2. Target Compressor Pressure:
        P_target = P_amb + (K_P * (N^2))
        3. Target Exhaust Gas Temperature:
        T_target = T_amb + (K_heat * W_f) - (K_cool * N)

        Args:
            current_fuel_flow (float): Commanded fuel flow rate (W_f) [kg/h].
            current_speed (float): Current engine rotational speed (N) [%].
            gain_constants (tuple[float, float, float, float]): Tuple of continuous physical gains:
                - speed_gain_coefficient (float): K_N speed gain coefficient [% / (kg/h)].
                - compressor_pressure_gain (float): K_P pressure gain coefficient [kPa / %^2].
                - combustion_heat_gain (float): K_heat combustion heat coefficient [°C / (kg/h)].
                - mass_overflow_cooling_gain (float): K_cool airflow cooling coefficient [°C / %].

        Returns:
            values_type: Tuple containing continuous target values:
                - target_rotational_speed (float): Target rotational speed (N_target) [%].
                - target_compressor_pressure (float): Target compressor pressure (P_target) [kPa].
                - target_exhaust_gas_temperature (float): Target exhaust temperature (T_target) [°C].
        """
        # Unpacks the gain constants.
        speed_gain_coefficient, compressor_pressure_gain,combustion_heat_gain, mass_overflow_cooling_gain = gain_constants

        # ------- Calculates target values. -------
        # Rotational Speed.
        target_rotational_speed: float = speed_gain_coefficient * current_fuel_flow

        # Compressor Pressure.
        target_compressor_pressure: float = self._cfg.ambient_pressure + (compressor_pressure_gain * (current_speed)**2)

        # Exhaust Gas Temperature.
        target_exhaust_gas_temperature: float = self._cfg.ambient_temperature + (combustion_heat_gain * current_fuel_flow) - (mass_overflow_cooling_gain * current_speed)

        return (target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature)

    def _calculate_derivatives(
            self,
            current_values: values_type,
            target_values: values_type
    ) -> values_type:
        """
        Calculates continuous time derivatives (rates of change) using physical time constants.

        Mathematical Formulations:
        1. dN/dt = (1 / tau_N) * (N_target - N)
        2. dP/dt = (1 / tau_P) * (P_target - P)
        3. dT/dt = (1 / tau_T) * (T_target - T)

        Args:
            current_values (values_type): Tuple of current engine states (N, P, T) in engineering units.
            target_values (values_type): Tuple of target steady-state values (N_target, P_target, T_target).

        Returns:
            values_type: Tuple of instantaneous time derivatives:
                - d_rotational_speed (float): Rotational speed rate of change (dN/dt) [%/s].
                - d_compressor_pressure (float): Compressor pressure rate of change (dP/dt) [kPa/s].
                - d_exhaust_gas_temperature (float): Exhaust gas temperature rate of change (dT/dt) [°C/s].
        """
        # Unpacks the parameters.
        current_rotational_speed, current_compressor_pressure, current_exhaust_gas_temperature = current_values
        target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature = target_values

        # ------- Calculates the derivatives. -------
        # Rotational Speed.
        d_rotational_speed: float = 1 / (self._cfg.rotor_inertial_time_const) * (target_rotational_speed - current_rotational_speed)

        # Compressor Pressure.
        d_compressor_pressure: float = 1 / (self._cfg.pressure_volume_time_const) * (target_compressor_pressure - current_compressor_pressure)

        # Exhaust Gas Temperature.
        d_exhaust_gas_temperature: float = 1 / (self._cfg.thermal_time_const) * (target_exhaust_gas_temperature - current_exhaust_gas_temperature)

        return (d_rotational_speed, d_compressor_pressure, d_exhaust_gas_temperature)

    def _calculate_next_step(
            self,
            current_values: values_type,
            derivative_values: values_type
    ) -> values_type:
        """
        Computes future state values for the subsequent simulation step using forward Euler integration.

        Mathematical Formulations:
        1. N[k+1] = N[k] + ((dN/dt)[k] * dt)
        2. P[k+1] = P[k] + ((dP/dt)[k] * dt)
        3. T[k+1] = T[k] + ((dT/dt)[k] * dt)

        Args:
            current_values (values_type): Tuple of states at step k (N[k], P[k], T[k]).
            derivative_values (values_type): Tuple of rates of change ((dN/dt)[k], (dP/dt)[k], (dT/dt)[k]).

        Returns:
            values_type: Tuple of integrated states for step k+1:
                - next_rotational_speed (float): Integrated rotational speed (N[k+1]) [%].
                - next_compressor_pressure (float): Integrated compressor pressure (P[k+1]) [kPa].
                - next_exhaust_gas_temperature (float): Integrated exhaust gas temperature (T[k+1]) [°C].
        """
        # Unpacks the parameters.
        current_rotational_speed, current_compressor_pressure, current_exhaust_gas_temperature = current_values
        d_rotational_speed, d_compressor_pressure, d_exhaust_gas_temperature = derivative_values

        # Uses the Euler equation to compute the values for the next step.
        next_rotational_speed: float = current_rotational_speed + (d_rotational_speed * self._cfg.simulation_step)

        next_compressor_pressure: float = current_compressor_pressure + (d_compressor_pressure * self._cfg.simulation_step)

        next_exhaust_gas_temperature: float = current_exhaust_gas_temperature + (d_exhaust_gas_temperature * self._cfg.simulation_step)

        return (next_rotational_speed, next_compressor_pressure, next_exhaust_gas_temperature)

    def run_simulation(
            self,
            initial_conditions: tuple[float, float, float]
    ) -> tuple[NDArray[float64], NDArray[float64], NDArray[float64], NDArray[float64], NDArray[float64]]:
        """
        Executes the continuous floating-point simulation across the full scheduled duration.

        At each discrete time step (dt):
        1. Evaluates fuel flow schedule based on simulation time.
        2. If structural trip occurs, zeroes fuel flow and disables system gains.
        3. Computes steady-state target values.
        4. Evaluates continuous time derivatives via physical time constants.
        5. Advances states using first-order forward Euler integration.
        6. Clamps states to physical baseline limits (N >= 0.0, P >= P_amb, T >= T_amb).
        7. Evaluates structural boundaries (overspeed N > N_max, thermal meltdown T > T_max).

        Args:
            initial_conditions (tuple[float, float, float]): Starting state vector at t = 0:
                - initial_speed (float): Initial rotational speed (N[0]) [%].
                - initial_pressure (float): Initial compressor pressure (P[0]) [kPa].
                - initial_temperature (float): Initial exhaust gas temperature (T[0]) [°C].

        Returns:
            tuple[NDArray[float64], NDArray[float64], NDArray[float64], NDArray[float64], NDArray[float64]]:
                Tuple of 5 logged floating-point NumPy arrays:
                - fuel_flow_history (NDArray[float64]): Commanded fuel flow over time [kg/h].
                - speed_history (NDArray[float64]): Rotational speed history [%].
                - pressure_history (NDArray[float64]): Compressor pressure history [kPa].
                - temperature_history (NDArray[float64]): Exhaust gas temperature history [°C].
                - time_history (NDArray[float64]): Simulation timestamps in seconds.
        """
        # Unpacks the initial conditions.
        initial_speed, initial_pressure, initial_temperature = initial_conditions

        # Calculates the total number of iterations needed.
        total_steps = int(
            np.ceil(self._cfg.total_simulation_time / self._cfg.simulation_step)
        )

        # Populates the time history as it is deterministic.
        time_history: NDArray[float64] = np.linspace(
            start = 0.0,
            stop = self._cfg.total_simulation_time,
            num = total_steps + 1
        )

        # Creates empty data structures.
        fuel_flow_history: NDArray[float64] = np.empty(
            total_steps + 1,
            np.float64
        )

        speed_history: NDArray[float64] = np.empty(
            total_steps + 1,
            np.float64
        )
        speed_history[0]= initial_speed

        pressure_history: NDArray[float64] = np.empty(
            total_steps + 1,
            np.float64
        )
        pressure_history[0]= initial_pressure

        temperature_history: NDArray[float64] = np.empty(
            total_steps + 1,
            np.float64
        )
        temperature_history[0]= initial_temperature

        # ------- Simulation Loop. -------
        is_engine_broken: bool = False

        # Defines local variables for the gains, so they can be modified if the engine breaks.
        speed_gain_coeff: float = self._cfg.speed_gain_coeff
        compressor_pressure_gain: float = self._cfg.compressor_pressure_gain
        combustion_heat_gain: float = self._cfg.combustion_heat_gain
        mass_overflow_cooling_gain: float = self._cfg.mass_overflow_cooling_gain

        for i in range(total_steps):
            # Calculates the current physical simulation time.
            k: float = i * self._cfg.simulation_step

            # Modifies the system behaviour, IF engine is broken.
            if is_engine_broken:
                # Simulates a cut-off.
                current_fuel_flow: float = 0.0

                speed_gain_coeff = 0.0
                compressor_pressure_gain = 0.0
                combustion_heat_gain = 0.0
                mass_overflow_cooling_gain = 0.0
                
            else:
                # Fetches the inputs.
                current_fuel_flow: float = self._fetch_current_fuel_flow(k = k)

            fuel_flow_history[i] = current_fuel_flow

            # Retrieves the current values.
            current_speed = speed_history[i]
            current_pressure = pressure_history[i]
            current_temperature = temperature_history[i]

            # Calculates the target values.
            target_speed, target_pressure, target_temperature = self._calculate_target_values(
                current_fuel_flow = current_fuel_flow,
                current_speed = current_speed,
                gain_constants = (speed_gain_coeff, compressor_pressure_gain, combustion_heat_gain, mass_overflow_cooling_gain)
            )

            # Calculates the derivatives.
            current_values: values_type = (current_speed, current_pressure, current_temperature)

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
            next_speed = max(next_speed, 0.0)

            next_pressure = max(next_pressure, self._cfg.ambient_pressure)

            next_temperature = max(next_temperature, self._cfg.ambient_temperature)

            # Monitors for maximum limit breaches.
            if (current_speed > self._cfg.max_rotational_speed) or \
                (current_temperature > self._cfg.max_compressor_temperature):
                is_engine_broken = True

            speed_history[i+1] = next_speed
            pressure_history[i+1] = next_pressure
            temperature_history[i+1] = next_temperature

        # Adds the last state of fuel flow to the history.
        last_fuel_flow: float = self._fetch_current_fuel_flow(k = (total_steps * self._cfg.simulation_step))

        fuel_flow_history[total_steps] = last_fuel_flow

        return (
            fuel_flow_history, speed_history, pressure_history, temperature_history, time_history
        )

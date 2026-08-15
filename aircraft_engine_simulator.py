
#* aircraft_engine_simulator.py

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
from numpy.typing import NDArray

#* ======= Aircraft Engine Simulator's Config Dataclass =======
@dataclass(frozen = True)
class ConfigAircraftEngineSimulator:
    #TODO AD, with the variable units such as ms, kPa.
    """
    """
    # ------- Simulation. -------
    simulation_step: float
    total_simulation_time: float

    # ------- Ambient Conditions. -------
    ambient_pressure: float
    ambient_temperature: float

    # ------- Time Constants (Inertia). -------
    rotor_inertial_time_constant: float
    pressure_volume_time_constant: float
    thermal_time_constant: float

    # ------- Gains. -------
    speed_gain_coefficient: float
    compressor_pressure_gain: float
    combustion_heat_gain: float
    mass_overflow_cooling_gain: float

    # ------- Engine Limits. -------
    max_rotational_speed: float
    max_compressor_temperature: float

#* ======= Aircraft Engine Simulator =======
values_type = tuple[float, float, float]

class AircraftEngineSimulator:
    #TODO AD
    def __init__(
            self,
            config_aircraft_engine_simulator: ConfigAircraftEngineSimulator
    ) -> None:
        self.cfg: ConfigAircraftEngineSimulator = config_aircraft_engine_simulator

    def _fetch_current_fuel_flow(
            self,
            k: float
    ) -> float:
        """ 
        #TODO Improve this docstring.
        This method gives back the value of fuel flow depending on
            the workflow declared in this method.
        """
        fuel_flow: float | None = None

        # Idle fuel flow.
        if (k == 0.0):
            fuel_flow = 10.0
        if (0.0 < k < 2.0):
            fuel_flow = 10.0

        # Throttle slam / rapic acceleration.
        elif (k == 2.0):
            fuel_flow = 90.0
        elif (2.0 < k < 18.0):
            fuel_flow = 90.

        # Throttle chop / deceleration.
        elif (k == 18.0):
            fuel_flow = 10.0
        elif (18.0 < k < self.cfg.total_simulation_time):
            fuel_flow = 10.0
        elif (k == self.cfg.total_simulation_time):
            fuel_flow = 10.0

        return fuel_flow

    def _calculate_target_values(
            self,
            current_fuel_flow: float,
            current_speed: float,
            gain_constants: tuple[float, float, float, float]
    ) -> values_type:
        # Unpacks the gain constants.
        speed_gain_coefficient, compressor_pressure_gain,combustion_heat_gain, mass_overflow_cooling_gain = gain_constants

        # ------- Calculates target values. -------
        # Rotational Speed.
        target_rotational_speed: float = speed_gain_coefficient * current_fuel_flow

        # Compressor Pressure.
        target_compressor_pressure: float = self.cfg.ambient_pressure + (compressor_pressure_gain * (current_speed)**2)

        # Exhaust Gas Temperature.
        target_exhaust_gas_temperature: float = self.cfg.ambient_temperature + (combustion_heat_gain * current_fuel_flow) - (mass_overflow_cooling_gain * current_speed)

        return (target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature)

    def _calculate_derivatives(
            self,
            current_values: values_type,
            target_values: values_type
    ) -> values_type:
        # Unpacks the parameters.
        current_rotational_speed, current_compressor_pressure, current_exhaust_gas_temperature = current_values
        target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature = target_values

        # ------- Calculates the derivatives. -------
        # Rotational Speed.
        d_rotational_speed: float = 1 / (self.cfg.rotor_inertial_time_constant) * (target_rotational_speed - current_rotational_speed)

        # Compressor Pressure.
        d_compressor_pressure: float = 1 / (self.cfg.pressure_volume_time_constant) * (target_compressor_pressure - current_compressor_pressure)

        # Exhaust Gas Temperature.
        d_exhaust_gas_temperature: float = 1 / (self.cfg.thermal_time_constant) * (target_exhaust_gas_temperature - current_exhaust_gas_temperature)

        return (d_rotational_speed, d_compressor_pressure, d_exhaust_gas_temperature)

    def _calculate_next_step(
            self,
            current_values: values_type,
            derivative_values: values_type
    ) -> values_type:
        # Unpacks the parameters.
        current_rotational_speed, current_compressor_pressure, current_exhaust_gas_temperature = current_values
        d_rotational_speed, d_compressor_pressure, d_exhaust_gas_temperature = derivative_values

        # Uses the Euler equation to compute the values for the next step.
        next_rotational_speed: float = current_rotational_speed + (d_rotational_speed * self.cfg.simulation_step)

        next_compressor_pressure: float = current_compressor_pressure + (d_compressor_pressure * self.cfg.simulation_step)

        next_exhaust_gas_temperature: float = current_exhaust_gas_temperature + (d_exhaust_gas_temperature * self.cfg.simulation_step)

        return (next_rotational_speed, next_compressor_pressure, next_exhaust_gas_temperature)

    def run_simulation(
            self,
            initial_conditions: tuple[float, float, float]
    ) -> tuple[NDArray, NDArray, NDArray, NDArray, NDArray]:
        # Unpacks the initial conditions.
        initial_speed, initial_pressure, initial_temperature = initial_conditions

        # Calculates the total number of iterations needed.
        total_steps = int(
            np.ceil(self.cfg.total_simulation_time / self.cfg.simulation_step)
        )

        # Populates the time history as it is deterministic.
        time_history = np.linspace(
            start = 0.0,
            stop = self.cfg.total_simulation_time,
            num = total_steps + 1
        )

        # Creates empty data structures.
        fuel_flow_history: NDArray = np.empty(
            total_steps + 1,
            np.float64
        )

        speed_history: NDArray = np.empty(
            total_steps + 1,
            np.float64
        )
        speed_history[0]= initial_speed

        pressure_history: NDArray = np.empty(
            total_steps + 1,
            np.float64
        )
        pressure_history[0]= initial_pressure

        temperature_history: NDArray = np.empty(
            total_steps + 1,
            np.float64
        )
        temperature_history[0]= initial_temperature

        # ------- Simulation Loop. -------
        is_engine_broken: bool = False

        # Defines local variables for the gains, so they can be modified if the engine breaks.
        speed_gain_coefficient: float = self.cfg.speed_gain_coefficient
        compressor_pressure_gain: float = self.cfg.compressor_pressure_gain
        combustion_heat_gain: float = self.cfg.combustion_heat_gain
        mass_overflow_cooling_gain: float = self.cfg.mass_overflow_cooling_gain

        for i in range(0, total_steps):
            # Calculates the current physical simulation time.
            k: float = i * self.cfg.simulation_step

            # Modifies the system behaviour, IF engine is broken.
            if is_engine_broken:
                # Simulates a cut-off.
                current_fuel_flow: float = 0.0

                speed_gain_coefficient = 0.0
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
                gain_constants = (speed_gain_coefficient, compressor_pressure_gain, combustion_heat_gain, mass_overflow_cooling_gain)
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
            if (next_speed < 0.0):
                next_speed = 0.0

            if (next_pressure < self.cfg.ambient_pressure):
                next_pressure = self.cfg.ambient_pressure

            if (next_temperature < self.cfg.ambient_temperature):
                next_temperature = self.cfg.ambient_temperature

            # Monitors for maximum limit breaches.
            if (current_speed > self.cfg.max_rotational_speed) or \
                (current_temperature > self.cfg.max_compressor_temperature):
                is_engine_broken = True

            speed_history[i+1] = next_speed
            pressure_history[i+1] = next_pressure
            temperature_history[i+1] = next_temperature

        # Adds the last state of fuel flow to the history.
        last_fuel_flow: float = self._fetch_current_fuel_flow(k = (total_steps * self.cfg.simulation_step))

        fuel_flow_history[total_steps] = last_fuel_flow

        return (
            fuel_flow_history, speed_history, pressure_history, temperature_history, time_history
        )

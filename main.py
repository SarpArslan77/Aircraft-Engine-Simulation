
#* main.py

#* ======= Libraries =======
# ------- Externals. -------
from numpy import float64
from numpy.typing import NDArray
from pathlib import Path

# ------- Customs. -------
from aircraft_engine_simulator_floating import (
    ConfigAircraftEngineSimulatorFloating,
    AircraftEngineSimulatorFloating
)

from quantize_floats import quantize_floats
from aircraft_engine_simulator_fixed_point import (
    ConfigAircraftEngineSimulatorFixedPoint,
    AircraftEngineSimulatorFixedPoint
)

from graph_visualizer import (
    ConfigGraphVisualizer,
    GraphVisualizer
)

#* ======= Main Loop =======
if __name__ == "__main__":
    # ------- Constants. -------
    # Declares only the constants, which are used in multiple places,
    #   otherwise they are directly declared in the class initializtion.
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
    MAX_COMPRESSOR_TEMPERATURE: float = 9500.0

    INT_BIT_WIDTH: int = 16
    FRACTIONAL_BIT_WIDTH: int = 16

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
    
        ambient_pressure_quantized = quantize_floats(AMBIENT_PRESSURE, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
        ambient_temperature_quantized = quantize_floats(AMBIENT_TEMPERATURE, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
    
        rotor_inertial_time_const_quantized = quantize_floats(ROTOR_INERTIAL_TIME_CONST, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
        pressure_volume_time_const_quantized = quantize_floats(PRESSURE_VOLUME_TIME_CONST, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
        thermal_time_const_quantized = quantize_floats(THERMAL_TIME_CONST, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
    
        speed_gain_coeff_quantized = quantize_floats(SPEED_GAIN_COEFF, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
        compressor_pressure_gain_quantized = quantize_floats(COMPRESSOR_PRESSURE_GAIN, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
        combustion_heat_gain_quantized = quantize_floats(COMBUSTION_HEAT_GAIN, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
        mass_overflow_cooling_gain_quantized = quantize_floats(MASS_OVERFLOW_COOLING_GAIN, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
    
        max_rotational_speed_quantized = quantize_floats(MAX_ROTATIONAL_SPEED, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),
        max_compressor_temperature_quantized = quantize_floats(MAX_COMPRESSOR_TEMPERATURE, INT_BIT_WIDTH, FRACTIONAL_BIT_WIDTH, True),

        software_results_file_path = Path(__file__).resolve().parent
    )
    
    aircraft_engine_simulator_fixed_point = AircraftEngineSimulatorFixedPoint(
        config_aircraft_engine_simulator_fixed_point = config_aircraft_engine_simulator_fixed_point
    )

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

    # Plots the data.
    graph_visualizer.run_visualization(
        histories_floating = (fuel_flow_history_floating, speed_history_floating, pressure_history_floating, temperature_history_floating),
        histories_fixed_point_scaled = (fuel_flow_history_fixed_point_scaled, speed_history_fixed_point_scaled, pressure_history_fixed_point_scaled, temperature_history_fixed_point_scaled),

        time_history = time_history
    )
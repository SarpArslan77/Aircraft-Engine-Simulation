
#* main.py

#* ======= Libraries =======
# ------- Customs. -------
from aircraft_engine_simulator import (
    ConfigAircraftEngineSimulator,
    AircraftEngineSimulator
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
    TOTAL_SIMULATION_TIME: float = 20.0 # [s].

    AMBIENT_PRESSURE: float = 101.3 # [kPa].
    AMBIENT_TEMPERATURE: float = 15.0
    MAX_ROTATIONAL_SPEED: float = 110.0

    # ------- Custom Classes. -------
    # Aircraft Engine.
    config_aircraft_engine_simulator = ConfigAircraftEngineSimulator(
        simulation_step = 1e-3,
        total_simulation_time = TOTAL_SIMULATION_TIME,

        ambient_pressure = AMBIENT_PRESSURE,
        ambient_temperature = AMBIENT_TEMPERATURE,

        rotor_inertial_time_constant = 1.5,
        pressure_volume_time_constant = 0.15,
        thermal_time_constant = 0.8,

        speed_gain_coefficient = 1.0,
        compressor_pressure_gain = 1.5e-2,
        combustion_heat_gain = 15.0,
        mass_overflow_cooling_gain = 6.0,

        max_rotational_speed = MAX_ROTATIONAL_SPEED,
        max_compressor_temperature = 9500.0
    )

    aircraft_engine_simulator = AircraftEngineSimulator(
        config_aircraft_engine_simulator = config_aircraft_engine_simulator
    )

    # Graph.
    config_graph_visualizer = ConfigGraphVisualizer(
        fuel_flow_linestyle = "--",
        fuel_flow_color = "gray",
        fuel_flow_linewidth = 1.5,

        speed_linestyle = "-",
        speed_color = "blue",
        speed_linewidth = 2.0,

        fuel_flow_and_speed_grid_linestyle = ":",
        fuel_flow_and_speed_grid_alpha = 0.6,

        pressure_linestyle = "-",
        pressure_color = "purple",
        pressure_linewidth = 2.0,

        pressure_grid_linestyle = ":",
        pressure_grid_alpha = 0.6,

        temperature_linestyle = "-",
        temperature_color = "red",
        temperature_linewidth = 2.0,

        temperature_grid_linestyle = ":",
        temperature_grid_alpha = 0.6,

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
    # Runs the aircraft engine simulation.
    fuel_flow_history, speed_history, pressure_history, temperature_history, time_history = aircraft_engine_simulator.run_simulation(
        initial_conditions = (0.0, AMBIENT_PRESSURE, AMBIENT_TEMPERATURE)
    )

    # Plots the data.
    graph_visualizer.run_visualization(
        fuel_flow_and_speed_histories = (fuel_flow_history, speed_history),
        pressure_history = pressure_history,
        temperature_history = temperature_history,

        time_history = time_history
    )
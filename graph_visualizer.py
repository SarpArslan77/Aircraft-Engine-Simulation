
#* graph_visualizer.py

#* ======= Libraries =======
# ------- Native. -------
from dataclasses import dataclass

# ------- Externals. -------
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

import numpy as np
from numpy.typing import NDArray

#* ======= Graph Visualizer's Config Dataclass =======
@dataclass(frozen = True)
class ConfigGraphVisualizer:
    # ------- Plot Attributes. -------
    # Fuel Flow and Speed.
    fuel_flow_linestyle: str
    fuel_flow_color: str
    fuel_flow_linewidth: float

    speed_linestyle: str
    speed_color: str
    speed_linewidth: float

    fuel_flow_and_speed_grid_linestyle: str
    fuel_flow_and_speed_grid_alpha: float

    # Pressure.
    pressure_linestyle: str
    pressure_color: str
    pressure_linewidth: float

    pressure_grid_linestyle: str
    pressure_grid_alpha: float

    # Temperature.
    temperature_linestyle: str
    temperature_color: str
    temperature_linewidth: float

    temperature_grid_linestyle: str
    temperature_grid_alpha: float

    # ------- Marker Conditions. -------
    max_speed: float

    engine_failure_line_color: str
    engine_failure_line_linestyle: str
    engine_failure_line_linewidth: float

    engine_failure_text_color: str
    engine_failure_text_fontsize: int
    engine_failure_text_fontweight: str

#* ======= Graph Visualizer =======
class GraphVisualizer:
    def __init__(
            self,
            config_graph_visualizer: ConfigGraphVisualizer
    ) -> None:
        self.cfg: ConfigGraphVisualizer = config_graph_visualizer

    def run_visualization(
            self,
            fuel_flow_and_speed_histories: tuple[NDArray, NDArray],
            pressure_history: NDArray,
            temperature_history: NDArray,

            time_history: NDArray
    ) -> None:
        # Unpacks the fuel flow and speed histories.
        fuel_flow_history, speed_history = fuel_flow_and_speed_histories
        
        # Creates the essentials for the plots.
        fig, (fuel_flow_and_speed_ax, pressure_ax, temperature_ax) = plt.subplots(
            3,
            1
        )
        fuel_flow_and_speed_ax: Axes
        pressure_ax: Axes
        temperature_ax: Axes

        axes: NDArray = np.array([fuel_flow_and_speed_ax, pressure_ax, temperature_ax])

        # ------- Plots the data. -------
        # Fuel Flow and Speed.
        fuel_flow_and_speed_ax.plot(
            time_history,
            fuel_flow_history,
            label = "Fuel Flow",
            linestyle = self.cfg.fuel_flow_linestyle,
            color = self.cfg.fuel_flow_color,
            linewidth = self.cfg.fuel_flow_linewidth
        )
        fuel_flow_and_speed_ax.plot(
            time_history,
            speed_history,
            label = "Rotational Speed",
            linestyle = self.cfg.speed_linestyle,
            color = self.cfg.speed_color,
            linewidth = self.cfg.speed_linewidth
        )

        fuel_flow_and_speed_ax.set_title("Fuel Flow & Rotational Speed over Time")
        fuel_flow_and_speed_ax.set_xlabel("Time [s]")
        fuel_flow_and_speed_ax.set_ylabel("[kg/h] / [%]")
        fuel_flow_and_speed_ax.grid(
            True,
            linestyle = self.cfg.fuel_flow_and_speed_grid_linestyle,
            alpha = self.cfg.fuel_flow_and_speed_grid_alpha
        )
        fuel_flow_and_speed_ax.legend(loc = "upper right")

        pressure_ax.plot(
            time_history,
            pressure_history,
            label = "Compressor Pressure",
            linestyle = self.cfg.pressure_linestyle,
            color = self.cfg.pressure_color,
            linewidth = self.cfg.pressure_linewidth
        )

        pressure_ax.set_title("Compressor Pressure over Time")
        pressure_ax.set_xlabel("Time [s]")
        pressure_ax.set_ylabel("[kPa]")
        pressure_ax.grid(
            True,
            linestyle = self.cfg.pressure_grid_linestyle,
            alpha = self.cfg.pressure_grid_alpha
        )
        pressure_ax.legend(loc = "lower right")

        temperature_ax.plot(
            time_history,
            temperature_history,
            label = "Exhaust Gas Temperature",
            linestyle = self.cfg.temperature_linestyle,
            color = self.cfg.temperature_color,
            linewidth = self.cfg.temperature_linewidth
        )

        temperature_ax.set_title("Exhaust Gas Temperature over Time")
        temperature_ax.set_xlabel("Time [s]")
        temperature_ax.set_ylabel("[*C]")
        temperature_ax.grid(
            True,
            linestyle = self.cfg.temperature_grid_linestyle,
            alpha = self.cfg.temperature_grid_alpha
        )
        temperature_ax.legend(loc = "lower right")

        # ------- Adds markars to the plots. -------
        # Vertical Failure Highlight Line.
        failure_indices: NDArray = np.where(speed_history > self.cfg.max_speed)
        did_it_fail: bool = (len(failure_indices[0]) > 0)

        if did_it_fail:
            first_failure_idx: int = failure_indices[0][0]
            failure_time: float = time_history[first_failure_idx]

            # Draws a vertical line and a small text across all subplots.
            for ax in axes:
                ax: Axes

                ax.axvline(
                    x = failure_time,
                    color = self.cfg.engine_failure_line_color,
                    linestyle = self.cfg.engine_failure_line_linestyle,
                    linewidth = self.cfg.engine_failure_line_linewidth,
                )

                # Gets the upper limit of the y-axis.
                _, ax_y_top_limit = ax.get_ylim()
                engine_failure_text_y_pos = ax_y_top_limit * 0.9

                ax.text(
                    x = failure_time + 1,
                    y = engine_failure_text_y_pos,
                    s = "Engine Failure",
                    color = self.cfg.engine_failure_text_color,
                    fontsize = self.cfg.engine_failure_text_fontsize,
                    fontweight = self.cfg.engine_failure_text_fontweight,
                    horizontalalignment = "left"
                )

        # Adjusts the layout automatically.
        fig.tight_layout()

        plt.show()
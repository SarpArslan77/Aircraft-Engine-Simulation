
#* graph_visualizer.py

#* ======= Libraries =======
# ------- Native. -------
from dataclasses import dataclass

# ------- Externals. -------
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.widgets import CheckButtons

import numpy as np
from numpy import (
    float64,
    int64
)
from numpy.typing import NDArray

#* ======= Graph Visualizer's Config Dataclass =======
@dataclass(frozen = True)
class ConfigGraphVisualizer:
    # ------- Plot Attributes. -------
    # Fuel Flow and Speed (Floating).
    fuel_flow_floating_linestyle: str
    fuel_flow_floating_color: str
    fuel_flow_floating_linewidth: float

    # Fuel Flow (Fixed Point).
    fuel_flow_fixed_point_linestyle: str
    fuel_flow_fixed_point_color: str
    fuel_flow_fixed_point_linewidth: float

    # Speed (Floating).
    speed_floating_linestyle: str
    speed_floating_color: str
    speed_floating_linewidth: float

    # Speed (Fixed Point).
    speed_fixed_point_linestyle: str
    speed_fixed_point_color: str
    speed_fixed_point_linewidth: float

    # Fuel Flow & Speed Grid.
    fuel_flow_and_speed_grid_linestyle: str
    fuel_flow_and_speed_grid_alpha: float

    # Pressure (Floating).
    pressure_floating_linestyle: str
    pressure_floating_color: str
    pressure_floating_linewidth: float

    # Pressure (Fixed Point).
    pressure_fixed_point_linestyle: str
    pressure_fixed_point_color: str
    pressure_fixed_point_linewidth: float

    # Pressure Grid.
    pressure_grid_linestyle: str
    pressure_grid_alpha: float

    # Temperature (Floating).
    temperature_floating_linestyle: str
    temperature_floating_color: str
    temperature_floating_linewidth: float

    # Temperature (Fixed Point).
    temperature_fixed_point_linestyle: str
    temperature_fixed_point_color: str
    temperature_fixed_point_linewidth: float

    # Temperature Grid.
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
histories_type = tuple[NDArray[float64 | int64], NDArray[float64 | int64], NDArray[float64 | int64], NDArray[float64 | int64]]

class GraphVisualizer:
    def __init__(
            self,
            config_graph_visualizer: ConfigGraphVisualizer
    ) -> None:
        self._cfg: ConfigGraphVisualizer = config_graph_visualizer

        # Stores active checkbox references to prevent garbage collection.
        self._checkboxes: list[CheckButtons] = []

    def _plot_data_history(
            self,
            ax: Axes,

            time_history: NDArray[float64],
            data_history: NDArray[float64 | int64],

            data_label: str,
            data_linestyle: str,
            data_color: str,
            data_linewidth: float,

            ax_title: str,
            ax_xlabel: str,
            ax_ylabel: str,

            grid_linestyle: str,
            grid_alpha: float,

            legend_loc: str
    ) -> Line2D:
        # Plots the data on the provided axes.
        line, = ax.plot(
            time_history,
            data_history,
            label = data_label,
            linestyle = data_linestyle,
            color = data_color,
            linewidth = data_linewidth
        )

        # Applies titles and labels if specified.
        if ax_title:
            ax.set_title(ax_title)
        if ax_xlabel:
            ax.set_xlabel(ax_xlabel)
        if ax_ylabel:
            ax.set_ylabel(ax_ylabel)

        # Applies grid configurations if specified.
        if (grid_linestyle) and (grid_alpha):
            ax.grid(
                True,
                linestyle = grid_linestyle,
                alpha = grid_alpha
            )

        # Puts the legend in the specified position.
        ax.legend(loc = legend_loc)

        return line

    def _add_failure_marker(
            self,
            failure_indices: NDArray[int64],
            time_history: NDArray[float64],
            axes: list[Axes]
    ) -> None:
        first_failure_idx = int(failure_indices[0][0])
        failure_time: float = time_history[first_failure_idx]

        # Draws a vertical line and a small text across all subplots.
        for ax in axes:
            ax: Axes
        
            ax.axvline(
                x = failure_time,
                color = self._cfg.engine_failure_line_color,
                linestyle = self._cfg.engine_failure_line_linestyle,
                linewidth = self._cfg.engine_failure_line_linewidth,
            )
        
            # Gets the upper limit of the y-axis.
            _, ax_y_top_limit = ax.get_ylim()
            engine_failure_text_y_pos = ax_y_top_limit * 0.9
        
            ax.text(
                x = failure_time + 1,
                y = engine_failure_text_y_pos,
                s = "Engine Failure",
                color = self._cfg.engine_failure_text_color,
                fontsize = self._cfg.engine_failure_text_fontsize,
                fontweight = self._cfg.engine_failure_text_fontweight,
                horizontalalignment = "left"
            )

    def __toggle_checkboxes(
            self,
            checkbox: CheckButtons,
            floating_lines: list[Line2D],
            fixed_point_lines: list[Line2D],
            fig: Figure
    ) -> None:
        # Queries the updated state of both checkboxes.
        floating_active, fixed_active = checkbox.get_status()

        for floating_line in floating_lines:
            floating_line: Line2D

            floating_line.set_visible(b = floating_active)

        for fixed_point_line in fixed_point_lines:
            fixed_point_line: Line2D

            fixed_point_line.set_visible(b = fixed_active)

        fig.canvas.draw_idle()

    def _setup_checkboxes(
            self,
            fig: Figure,
            ax: Axes,
            floating_lines: list[Line2D],
            fixed_point_lines: list[Line2D]
    ) -> CheckButtons:
        # 'CheckButtons' allow checkboxes to toggle individual modes.
        # ? actives: Initial check state of the buttons.
        checkbox = CheckButtons(
            ax,
            ("Floating", "Fixed Point"),
            actives = (True, True)
        )

        # Passes a callable that executes the toggle method.
        checkbox.on_clicked(
            lambda label: self.__toggle_checkboxes(
                checkbox = checkbox,
                floating_lines = floating_lines,
                fixed_point_lines = fixed_point_lines,
                fig = fig
            )
        )

        return checkbox

    def run_visualization(
            self,
            histories_floating: histories_type,
            histories_fixed_point_scaled: histories_type,

            time_history: NDArray[float64]
    ) -> None:
        # Unpacks the fuel flow and speed histories.
        fuel_flow_history_floating, speed_history_floating, pressure_history_floating, temperature_history_floating = histories_floating
        fuel_flow_history_fixed_point, speed_history_fixed_point, pressure_history_fixed_point, temperature_history_fixed_point = histories_fixed_point_scaled

        # Clear any existing checkboxes to avoid leaks in successive runs
        self._checkboxes.clear()

        # ------- Plots the datas. -------
        # Fuel Flow and Rotational Speed.
        fuel_flow_and_speed_fig, fuel_flow_and_speed_ax = plt.subplots(1, 1)
        fuel_flow_and_speed_ax: Axes

        line_fuel_flow_floating = self._plot_data_history(
            ax = fuel_flow_and_speed_ax,
            time_history = time_history,
            data_history = fuel_flow_history_floating,
            data_label = "Fuel Flow (Floating)",
            data_linestyle = self._cfg.fuel_flow_floating_linestyle,
            data_color = self._cfg.fuel_flow_floating_color,
            data_linewidth = self._cfg.fuel_flow_floating_linewidth,
            ax_title = "Fuel Flow & Rotational Speed over Time",
            ax_xlabel = "Time [s]",
            ax_ylabel = "[kg/h] / [%]",
            grid_linestyle = self._cfg.fuel_flow_and_speed_grid_linestyle,
            grid_alpha = self._cfg.fuel_flow_and_speed_grid_alpha,
            legend_loc = "upper right"
        )

        line_fuel_flow_fixed_point = self._plot_data_history(
            ax = fuel_flow_and_speed_ax,
            time_history = time_history,
            data_history = fuel_flow_history_fixed_point,
            data_label = "Fuel Flow (Fixed Point)",
            data_linestyle = self._cfg.fuel_flow_fixed_point_linestyle,
            data_color = self._cfg.fuel_flow_fixed_point_color,
            data_linewidth = self._cfg.fuel_flow_fixed_point_linewidth,
            ax_title = "Fuel Flow & Rotational Speed over Time",
            ax_xlabel = "Time [s]",
            ax_ylabel = "[kg/h] / [%]",
            grid_linestyle = self._cfg.fuel_flow_and_speed_grid_linestyle,
            grid_alpha = self._cfg.fuel_flow_and_speed_grid_alpha,
            legend_loc = "upper right"
        )

        line_speed_floating = self._plot_data_history(
            ax = fuel_flow_and_speed_ax,
            time_history = time_history,
            data_history = speed_history_floating,
            data_label = "Rotational Speed (Floating)",
            data_linestyle = self._cfg.speed_floating_linestyle,
            data_color = self._cfg.speed_floating_color,
            data_linewidth = self._cfg.speed_floating_linewidth,
            ax_title = "Fuel Flow & Rotational Speed over Time",
            ax_xlabel = "Time [s]",
            ax_ylabel = "[kg/h] / [%]",
            grid_linestyle = self._cfg.fuel_flow_and_speed_grid_linestyle,
            grid_alpha = self._cfg.fuel_flow_and_speed_grid_alpha,
            legend_loc = "upper right"
        )

        line_speed_fixed_point = self._plot_data_history(
            ax = fuel_flow_and_speed_ax,
            time_history = time_history,
            data_history = speed_history_fixed_point,
            data_label = "Rotational Speed (Fixed Point)",
            data_linestyle = self._cfg.speed_fixed_point_linestyle,
            data_color = self._cfg.speed_fixed_point_color,
            data_linewidth = self._cfg.speed_fixed_point_linewidth,
            ax_title = "Fuel Flow & Rotational Speed over Time",
            ax_xlabel = "Time [s]",
            ax_ylabel = "[kg/h] / [%]",
            grid_linestyle = self._cfg.fuel_flow_and_speed_grid_linestyle,
            grid_alpha = self._cfg.fuel_flow_and_speed_grid_alpha,
            legend_loc = "upper right"
        )

        # Compressor Pressure.
        pressure_fig, pressure_ax = plt.subplots(1, 1)
        pressure_ax: Axes

        line_pressure_floating = self._plot_data_history(
            ax = pressure_ax,
            time_history = time_history,
            data_history = pressure_history_floating,
            data_label = "Compressor Pressure (Floating)",
            data_linestyle = self._cfg.pressure_floating_linestyle,
            data_color = self._cfg.pressure_floating_color,
            data_linewidth = self._cfg.pressure_floating_linewidth,
            ax_title = "Compressor Pressure over Time",
            ax_xlabel = "Time [s]",
            ax_ylabel = "[kPa]",
            grid_linestyle = self._cfg.pressure_grid_linestyle,
            grid_alpha = self._cfg.pressure_grid_alpha,
            legend_loc = "lower right"
        )

        line_pressure_fixed_point = self._plot_data_history(
            ax = pressure_ax,
            time_history = time_history,
            data_history = pressure_history_fixed_point,
            data_label = "Compressor Pressure (Fixed Point)",
            data_linestyle = self._cfg.pressure_fixed_point_linestyle,
            data_color = self._cfg.pressure_fixed_point_color,
            data_linewidth = self._cfg.pressure_fixed_point_linewidth,
            ax_title = "Compressor Pressure over Time",
            ax_xlabel = "Time [s]",
            ax_ylabel = "[kPa]",
            grid_linestyle = self._cfg.pressure_grid_linestyle,
            grid_alpha = self._cfg.pressure_grid_alpha,
            legend_loc = "lower right"
        )

        # Exhaust Gas Temperature.
        temperature_fig, temperature_ax = plt.subplots(1, 1)
        temperature_ax: Axes

        line_temperature_floating = self._plot_data_history(
            ax = temperature_ax,
            time_history = time_history,
            data_history = temperature_history_floating,
            data_label = "Exhaust Gas Temperature (Floating)",
            data_linestyle = self._cfg.temperature_floating_linestyle,
            data_color = self._cfg.temperature_floating_color,
            data_linewidth = self._cfg.temperature_floating_linewidth,
            ax_title = "Exhaust Gas Temperature over Time",
            ax_xlabel = "Time [s]",
            ax_ylabel = "[*C]",
            grid_linestyle = self._cfg.temperature_grid_linestyle,
            grid_alpha = self._cfg.temperature_grid_alpha,
            legend_loc = "lower right"
        )

        line_temperature_fixed_point = self._plot_data_history(
            ax = temperature_ax,
            time_history = time_history,
            data_history = temperature_history_fixed_point,
            data_label = "Exhaust Gas Temperature (Fixed Point)",
            data_linestyle = self._cfg.temperature_fixed_point_linestyle,
            data_color = self._cfg.temperature_fixed_point_color,
            data_linewidth = self._cfg.temperature_fixed_point_linewidth,
            ax_title = "Exhaust Gas Temperature over Time",
            ax_xlabel = "Time [s]",
            ax_ylabel = "[*C]",
            grid_linestyle = self._cfg.temperature_grid_linestyle,
            grid_alpha = self._cfg.temperature_grid_alpha,
            legend_loc = "lower right"
        )

        # ------- Finalize layout on standard axes. -------
        fuel_flow_and_speed_fig.tight_layout()
        fuel_flow_and_speed_fig.subplots_adjust(left = 0.25)

        pressure_fig.tight_layout()
        pressure_fig.subplots_adjust(left = 0.25)

        temperature_fig.tight_layout()
        temperature_fig.subplots_adjust(left = 0.25)

        # ------- Adds custom manual axes (checkboxes). -------
        checkboxes_ax_fuel_flow_and_speed: Axes = fuel_flow_and_speed_fig.add_axes([0.02, 0.7, 0.18, 0.15])
        checkboxes_ax_fuel_flow_and_speed.set_title(
            label = "Display Mode",
            fontsize = 9,
            fontweight = "bold"
        )
        cb_flow_speed = self._setup_checkboxes(
            fig = fuel_flow_and_speed_fig,
            ax = checkboxes_ax_fuel_flow_and_speed,
            floating_lines = [line_fuel_flow_floating, line_speed_floating],
            fixed_point_lines = [line_fuel_flow_fixed_point, line_speed_fixed_point]
        )
        self._checkboxes.append(cb_flow_speed)

        # Setups checkboxes for pressure.
        checkboxes_ax_pressure: Axes = pressure_fig.add_axes([0.02, 0.7, 0.18, 0.15])
        checkboxes_ax_pressure.set_title(
            label = "Display Mode",
            fontsize = 9,
            fontweight = "bold"
        )
        cb_pressure = self._setup_checkboxes(
            fig = pressure_fig,
            ax = checkboxes_ax_pressure,
            floating_lines = [line_pressure_floating],
            fixed_point_lines = [line_pressure_fixed_point]
        )
        self._checkboxes.append(cb_pressure)

        # Setups checkboxes for temperature.
        checkbox_ax_temp: Axes = temperature_fig.add_axes([0.02, 0.7, 0.18, 0.15])
        checkbox_ax_temp.set_title(
            label = "Display Mode",
            fontsize = 9,
            fontweight = "bold"
        )
        cb_temp = self._setup_checkboxes(
            fig = temperature_fig,
            ax = checkbox_ax_temp,
            floating_lines = [line_temperature_floating],
            fixed_point_lines = [line_temperature_fixed_point]
        )
        self._checkboxes.append(cb_temp)

        # ------- Adds markers to the plots -------
        # Vertical Failure Highlight Line.
        failure_indices: NDArray[int64] = np.where(speed_history_floating > self._cfg.max_speed)
        did_it_fail: bool = (len(failure_indices[0]) > 0)

        axes: list[Axes] = [fuel_flow_and_speed_ax, pressure_ax, temperature_ax]

        if did_it_fail:
            self._add_failure_marker(
                failure_indices = failure_indices,
                time_history = time_history,
                axes = axes
            )

        plt.show()
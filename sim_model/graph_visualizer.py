
#* sim_model/graph_visualizer.py

#* ======= Libraries =======
# ------- Native. -------
from dataclasses import dataclass

# ------- Externals. -------
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.widgets import CheckButtons
from numpy import float64, int64
from numpy.typing import NDArray


#* ======= Graph Visualizer's Config Dataclass =======
@dataclass(frozen = True)
class ConfigGraphVisualizer:
    """
    Configuration dataclass defining styling and threshold parameters for telemetry plots.

    Encapsulates Matplotlib rendering styles (colors, linestyles, linewidths, and alphas)
    for side-by-side floating-point and fixed-point telemetry comparison, as well as
    annotations for physical failure markers.

    Attributes:
        fuel_flow_floating_linestyle (str): Linestyle for floating-point fuel flow curve.
        fuel_flow_floating_color (str): Matplotlib color string for floating-point fuel flow.
        fuel_flow_floating_linewidth (float): Line width for floating-point fuel flow curve.
        fuel_flow_fixed_point_linestyle (str): Linestyle for fixed-point fuel flow curve.
        fuel_flow_fixed_point_color (str): Matplotlib color string for fixed-point fuel flow.
        fuel_flow_fixed_point_linewidth (float): Line width for fixed-point fuel flow curve.
        speed_floating_linestyle (str): Linestyle for floating-point rotational speed curve.
        speed_floating_color (str): Matplotlib color string for floating-point rotational speed.
        speed_floating_linewidth (float): Line width for floating-point rotational speed curve.
        speed_fixed_point_linestyle (str): Linestyle for fixed-point rotational speed curve.
        speed_fixed_point_color (str): Matplotlib color string for fixed-point rotational speed.
        speed_fixed_point_linewidth (float): Line width for fixed-point rotational speed curve.
        fuel_flow_and_speed_grid_linestyle (str): Linestyle for fuel flow and speed subplot grid.
        fuel_flow_and_speed_grid_alpha (float): Opacity alpha factor for fuel flow and speed grid.
        pressure_floating_linestyle (str): Linestyle for floating-point compressor pressure curve.
        pressure_floating_color (str): Matplotlib color string for floating-point compressor pressure.
        pressure_floating_linewidth (float): Line width for floating-point compressor pressure curve.
        pressure_fixed_point_linestyle (str): Linestyle for fixed-point compressor pressure curve.
        pressure_fixed_point_color (str): Matplotlib color string for fixed-point compressor pressure.
        pressure_fixed_point_linewidth (float): Line width for fixed-point compressor pressure curve.
        pressure_grid_linestyle (str): Linestyle for compressor pressure subplot grid.
        pressure_grid_alpha (float): Opacity alpha factor for compressor pressure grid.
        temperature_floating_linestyle (str): Linestyle for floating-point exhaust temperature curve.
        temperature_floating_color (str): Matplotlib color string for floating-point exhaust temperature.
        temperature_floating_linewidth (float): Line width for floating-point exhaust temperature curve.
        temperature_fixed_point_linestyle (str): Linestyle for fixed-point exhaust temperature curve.
        temperature_fixed_point_color (str): Matplotlib color string for fixed-point exhaust temperature.
        temperature_fixed_point_linewidth (float): Line width for fixed-point exhaust temperature curve.
        temperature_grid_linestyle (str): Linestyle for exhaust temperature subplot grid.
        temperature_grid_alpha (float): Opacity alpha factor for exhaust temperature grid.
        max_speed (float): Rotational speed threshold above which an engine overspeed failure occurs [%].
        engine_failure_line_color (str): Color of the vertical marker indicating engine failure.
        engine_failure_line_linestyle (str): Linestyle of the vertical engine failure marker.
        engine_failure_line_linewidth (float): Line width of the vertical engine failure marker.
        engine_failure_text_color (str): Color of the failure annotation label.
        engine_failure_text_fontsize (int): Font size for the failure annotation label.
        engine_failure_text_fontweight (str): Font weight for the failure annotation label.
    """
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
    """
    Interactive telemetry visualizer for engine simulation histories.

    Constructs dedicated Matplotlib subplots for engine operational states:
    1. Fuel Flow and Rotational Speed over time.
    2. Compressor Pressure over time.
    3. Exhaust Gas Temperature (EGT) over time.

    Integrates interactive checkbox widgets to selectively toggle continuous floating-point
    reference traces and quantized fixed-point responses independently, and detects and marks
    structural failure boundary events.
    """
    def __init__(
            self,
            config_graph_visualizer: ConfigGraphVisualizer
    ) -> None:
        """
        Initializes the GraphVisualizer with rendering and styling parameters.

        Args:
            config_graph_visualizer (ConfigGraphVisualizer): Configuration dataclass containing
                visual parameters, line properties, grid styles, and failure criteria.

        Returns:
            None
        """
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
        """
        Plots a state trajectory array onto a specified Matplotlib axis with styling configurations.

        Configures label identifiers, color, line styles, axis titles, labels, optional grid lines,
        and sets legend placement.

        Args:
            ax (Axes): Target Matplotlib axis object to plot onto.
            time_history (NDArray[float64]): Array of simulation time points [s].
            data_history (NDArray[float64 | int64]): Logged physical or scaled state telemetry values.
            data_label (str): Label string for legend display.
            data_linestyle (str): Line style pattern (e.g., '-', '--', ':').
            data_color (str): Matplotlib color identifier string.
            data_linewidth (float): Line stroke width.
            ax_title (str): Subplot title string (empty string to omit).
            ax_xlabel (str): Horizontal axis label string (empty string to omit).
            ax_ylabel (str): Vertical axis label string (empty string to omit).
            grid_linestyle (str): Grid line style pattern (empty string to omit grid).
            grid_alpha (float): Opacity factor for the background grid lines.
            legend_loc (str): Legend positioning string (e.g., 'upper right', 'lower right').

        Returns:
            Line2D: The constructed 2D line plot object.
        """
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
        """
        Draws vertical failure marker lines and text annotations across all telemetry axes.

        Locates the exact simulation timestamp where engine limits were first breached
        and renders a vertical threshold line and descriptive label across the supplied subplots.

        Args:
            failure_indices (NDArray[int64]): Indices of simulation steps where engine speed exceeded max_speed.
            time_history (NDArray[float64]): Array of physical simulation timestamps in seconds.
            axes (list[Axes]): List of active Matplotlib subplot axes to annotate.

        Returns:
            None
        """
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
        """
        Callback handler updating line visibility when display mode checkboxes are toggled.

        Queries checkbox states and toggles visibility of floating-point and fixed-point
        Line2D traces dynamically without requiring a full figure redraw.

        Args:
            checkbox (CheckButtons): Interactive Matplotlib CheckButtons widget instance.
            floating_lines (list[Line2D]): Traces associated with floating-point reference data.
            fixed_point_lines (list[Line2D]): Traces associated with fixed-point model data.
            fig (Figure): Target Matplotlib figure to refresh.

        Returns:
            None
        """
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
        """
        Instantiates interactive CheckButtons widgets on a dedicated figure axis.

        Configures check states for 'Floating' and 'Fixed Point' traces and binds visibility
        toggle callbacks to the associated plot lines.

        Args:
            fig (Figure): Target Matplotlib figure owning the axes.
            ax (Axes): Dedicated manual axis reserved for the checkbox widget.
            floating_lines (list[Line2D]): List of plotted lines representing floating-point traces.
            fixed_point_lines (list[Line2D]): List of plotted lines representing fixed-point traces.

        Returns:
            CheckButtons: The initialized interactive checkbox controller instance.
        """
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

            time_history: NDArray[float64],

            show_plots: bool
    ) -> None:
        """
        Constructs and renders the full multi-window engine telemetry inspection dashboard.

        Plots side-by-side comparative curves for continuous floating-point and scaled fixed-point
        simulations across three independent figures:
        - Fuel Flow & Rotational Speed
        - Compressor Pressure
        - Exhaust Gas Temperature

        Configures interactive visibility checkboxes for both data modes, attaches failure
        event markers if operational limits were breached, and optionally displays plots via GUI.

        Args:
            histories_floating (histories_type): 4-tuple of floating-point reference arrays
                (fuel_flow, speed, pressure, temperature).
            histories_fixed_point_scaled (histories_type): 4-tuple of scaled fixed-point arrays
                (fuel_flow, speed, pressure, temperature).
            time_history (NDArray[float64]): Physical simulation time steps in seconds.
            show_plots (bool): Flag indicating whether to invoke plt.show() to block and display UI.

        Returns:
            None
        """
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

        if show_plots:
            plt.show()
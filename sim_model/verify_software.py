
#* sim_model/verify_software.py

#* ======= Libraries =======
# ------- Externals. -------
import numpy as np
from numpy import float64, inf
from numpy.typing import NDArray


#* ======= Software Verifier =======
class SoftwareVerifier:
    """
    Statistical accuracy and numerical noise analyzer for fixed-point quantization verification.

    Evaluates deviation between continuous floating-point golden reference signals and scaled
    fixed-point simulation trajectories using standard signal processing metrics:
    Mean Absolute Error (MAE), Maximum Error (ME), Mean Squared Error (MSE), Root-Mean-Squared
    Error (RMSE), and Signal-to-Quantization-Noise Ratio (SQNR).
    """
    def __init__(self) -> None:
        """
        Initializes the SoftwareVerifier numerical assessment instance.

        Returns:
            None
        """
        pass

    def _calculate_mae(
            self,
            error: NDArray[float64]
    ) -> float:
        """
        Calculates the Mean Absolute Error (MAE) between reference and quantized signals.

        Mathematical Formulation:
        MAE = (1 / N) * sum(|error|)

        Args:
            error (NDArray[float64]): Residual error array (reference_signal - quantized_scaled_signal).

        Returns:
            float: Mean Absolute Error value across all time samples.
        """
        return float(np.mean(np.abs(error)))

    def _calculate_max_error(
            self,
            error: NDArray[float64]
    ) -> float:
        """
        Calculates the Maximum Absolute Error (ME) observed across the trajectory.

        Mathematical Formulation:
        ME = max(|error|)

        Args:
            error (NDArray[float64]): Residual error array (reference_signal - quantized_scaled_signal).

        Returns:
            float: Peak absolute deviation across the simulation.
        """
        return float(np.max(np.abs(error)))

    def _calculate_mse_and_rmse(
            self,
            error: NDArray[float64]
    ) -> tuple[float, float]:
        """
        Computes Mean Squared Error (MSE) and Root-Mean-Square Error (RMSE).

        Mathematical Formulations:
        1. MSE = (1 / N) * sum(error^2)
        2. RMSE = sqrt(MSE)

        Args:
            error (NDArray[float64]): Residual error array (reference_signal - quantized_scaled_signal).

        Returns:
            tuple[float, float]: Tuple containing:
                - mse (float): Mean Squared Error.
                - rmse (float): Root-Mean-Square Error.
        """
        # Calculates the MSE and then roots it for RMSE.
        mse = float(np.mean(error**2))

        rmse = float(np.sqrt(mse))

        return (mse, rmse)

    def _calculate_sqnr(
            self,
            original_signal: NDArray[float64],
            error: NDArray[float64]
    ) -> float:
        """
        Calculates the Signal-to-Quantization-Noise Ratio (SQNR) in decibels (dB).

        Measures signal degradation introduced by fixed-point wordlength truncation.
        Safely handles zero-power edge cases by returning +/- infinity.

        Mathematical Formulation:
        SQNR = 10 * log10(sum(signal^2) / sum(error^2)) [dB]

        Args:
            original_signal (NDArray[float64]): Baseline continuous floating-point golden reference signal array.
            error (NDArray[float64]): Residual quantization error array (original_signal - quantized_signal).

        Returns:
            float: Signal-to-Quantization-Noise Ratio in decibels [dB], or +/-inf on edge cases.
        """
        # ------- Calculates SQNR. -------
        # Calculates the signals powers.
        original_signal_power: NDArray[float64] = original_signal ** 2
        error_power: NDArray[float64] = error ** 2

        # Sums the power of each element.
        original_signal_power_summed: float = np.sum(a = original_signal_power)
        error_power_summed: float = np.sum(a = error_power)

        # Handles the edge cases for the return values.
        if (original_signal_power_summed == 0.0):
            return (-inf)
        elif (error_power_summed == 0.0):
            return inf
        else:
            return float(10 * np.log10(original_signal_power_summed / error_power_summed)) # [dB].

    def run_software_verifier(
            self,
            original_signal: NDArray[float64],
            error: NDArray[float64],
            state_name: str
    ) -> None:
        """
        Evaluates and prints all numerical precision and quantization error metrics for a state.

        Computes MAE, ME, MSE, RMSE, and SQNR for the given state trajectory and prints a formatted
        summary to standard output for verification auditing.

        Args:
            original_signal (NDArray[float64]): Continuous floating-point reference signal array.
            error (NDArray[float64]): Residual error array (original_signal - quantized_scaled_signal).
            state_name (str): Descriptive identifier of the engine state (e.g., 'Rotational Speed').

        Returns:
            None
        """
        # Calculates different metrics and logs them.
        # Mean Absolute Error (MAE).
        mae: float = self._calculate_mae(error = error)

        # Max Error (ME).
        me: float = self._calculate_max_error(error = error)

        # Mean Squared Error (MSE) & Root-Mean Squared Error (RMSE).
        mse, rmse = self._calculate_mse_and_rmse(error = error)

        # Signal-to-Quantization-Noise Ratio (SQNR).
        sqnr: float = self._calculate_sqnr(
            original_signal = original_signal,
            error = error
        )

        print(f" --> State: {state_name} <-- ")
        print(f"MAE: {mae:.4f} | ME: {me:.4f} | MSE: {mse:.4f} , RMSE: {rmse:.4f} | sqnr: {sqnr:.4f} dB")

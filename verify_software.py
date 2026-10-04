
#* verify_software.py

#* ======= Libraries =======
# ------- Native. -------

# ------- Externals. -------
import numpy as np
from numpy.typing import NDArray
from numpy import (
    float64, 
    inf
)

#* ======= Software Verifier =======
class SoftwareVerifier:
    def __init__(self) -> None:
        pass

    def _calculate_mae(
            self,
            error: NDArray
    ) -> float:
        return float(np.max(np.abs(error)))

    def _calculate_mse_and_rmse(
            self,
            error: NDArray
    ) -> tuple[float, float]:
        # Calculates the MSE and then roots it for RMSE.
        mse = float(np.mean(error**2))

        rmse = float(np.sqrt(mse))

        return (mse, rmse)

    def _calculate_sqnr(
            self,
            original_signal: NDArray,
            error: NDArray
    ) -> float:
        # ------- Calculates SQNR. -------
        # Calculates the signals powers.
        original_signal_power: NDArray = original_signal ** 2
        error_power: NDArray = error ** 2

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
            original_signal: NDArray,
            error: NDArray,
            state_name: str
    ) -> tuple[float, float, float, float]:
        # Calculates different metrics and logs them.
        # Mean Absolute Error (MAE).
        mae: float = self._calculate_mae(error = error)

        # Mean Squared Error (MSE) & Root-Mean Squared Error (RMSE).
        mse, rmse = self._calculate_mse_and_rmse(error = error)

        # Signal-to-Quantization-Noise Ratio (SQNR).
        sqnr: float = self._calculate_sqnr(
            original_signal = original_signal,
            error = error
        )

        print(f" --> State: {state_name} <-- ")
        print(f"MAE: {mae:4f} | MSE: {mse:4f} , RMSE: {rmse:4f} | sqnr: {sqnr:4f} dB")

        return (mae, mse, rmse, sqnr)

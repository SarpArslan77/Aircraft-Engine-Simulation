
#* verify_software.py

#* ======= Libraries =======
# ------- Native. -------

# ------- Externals. -------
import numpy as np
from numpy.typing import NDArray
from numpy import float64

#* ======= Software Verifier =======
class SoftwareVerifier:
    def __init__(self) -> None:
        pass

    def _calculate_mae(
            self,
            error: NDArray
    ) -> float:
        return float(np.max(np.abs(error)))

    def _calculate_rmse(
            self,
            error: NDArray
    ) -> tuple[float, float]:
        # Calculates the mean square error and then roots it.
        mse: float64 = np.mean(error**2)

        rmse = float(np.sqrt(mse))

        return (mse, rmse)

    def _calculate_sqnr(
            self,
            mse: float,
            signal_power: float
    ) -> float:
        

    def run_software_verifier(
            self
    ) -> None:
        pass

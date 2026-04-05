"""Processing package: reusable telemetry math and fusion blocks."""

from processing.ekf_core import (
    calculate_kalman_gain,
    f_state_transition,
    get_jacobian_F,
    predict_covariance,
    update_covariance,
    update_state,
)
from processing.ekf_runner import run_ekf_on_log
from processing.geodesy import haversine, llh_to_ned, normalize_gps_measurement
from processing.integration import calculate_magnitude, trapz_step
from processing.orientation import euler_to_rotation_matrix, rotate_vector

__all__ = [
    "haversine",
    "llh_to_ned",
    "normalize_gps_measurement",
    "euler_to_rotation_matrix",
    "rotate_vector",
    "f_state_transition",
    "get_jacobian_F",
    "predict_covariance",
    "calculate_kalman_gain",
    "update_state",
    "update_covariance",
    "trapz_step",
    "calculate_magnitude",
    "run_ekf_on_log",
]

# Mathematical Grounding in Code

This page shows where the project's **comments and documentation explain the mathematics** behind the key transforms: the Euler-angle kinematic singularity (gimbal lock) and its workaround, the physical meaning of accelerometer output (specific force), and the error behaviour of IMU double integration.

---

## Euler kinematics and the gimbal lock singularity

### Why it matters

Body attitude is represented as three Euler angles — roll (φ), pitch (θ), yaw (ψ) — in the ZYX convention. Converting body-frame angular rates (p, q, r) to Euler rates requires dividing by **cos(θ)**:

```
φ̇ = p + (q sin φ + r cos φ) tan θ
θ̇ = q cos φ − r sin φ
ψ̇ = (q sin φ + r cos φ) / cos θ
```

When **θ → ±90°**, **cos(θ) → 0** and the yaw rate diverges — this is the **gimbal lock singularity**: the ZYX parameterization loses a degree of freedom and angular rates become numerically undefined.

**Quaternions** (unit quaternions on S³) represent the same rotation without any trigonometric denominator, so they avoid this class of singularity entirely. Navigation-grade attitude filters often use a quaternion state specifically for that reason.

### How it is handled in this project

The EKF attitude state uses Euler angles. The kinematic update in `service/fusion/ekf_core.py` names the singularity in a comment and branches around it:

```python title="service/fusion/ekf_core.py"
        # Euler kinematics: convert body rates (p, q, r) to Euler rates
        if abs(cp) > 1e-6:  # Prevent gimbal lock singularity
            roll  += (p + q * sr * tp + r * cr * tp) * dt
            pitch += (q * cr - r * sr) * dt
            yaw   += (q * sr / cp + r * cr / cp) * dt
        else:
            # Fallback if pitched near 90 degrees
            roll  += p * dt
            pitch += q * dt
            yaw   += r * dt
```

`cp` is `cos(pitch)`. The guard `abs(cp) > 1e-6` detects the near-singular region and replaces the full kinematic equations with a simplified body-rate integration. The comment **names gimbal lock** and makes the geometric reason for the guard explicit. Switching to a quaternion state would remove the need for this fallback but would change the filter's state vector and update equations.

The attitude panel in `drone_dashboard.py` (`build_attitude_panel`) reads these Euler angles directly from the `ATT` log messages and plots roll, pitch, and yaw — actual versus desired — so the singularity range (pitch near ±90°) is visible in the UI if it occurs.

---

## Specific force, gravity compensation, and double integration

### What an accelerometer actually measures

An accelerometer does **not** measure kinematic acceleration. It measures **specific force** — the non-gravitational force per unit mass:

```
a_measured = a_true − g_vector
```

At rest on a flat surface the sensor reads roughly +9.81 m/s² upward (reacting to the normal force), not zero. To recover true kinematic acceleration the gravity vector must be added back **in the navigation frame** after rotating the measurement from body to NED.

The EKF prediction step documents this in `service/fusion/ekf_core.py`:

```python title="service/fusion/ekf_core.py"
    # Convert raw acceleration to dynamic acceleration in NED.
    # In NED, gravity is a downward vector [0, 0, g].
    # Accelerometer measures specific force: a_meas = a_true - g_vector.
    # Therefore, a_true = a_meas + g_vector.
    acc_nav_dyn = acc_nav.copy()
    acc_nav_dyn[2] += GRAVITY_MS2
```

### Why double integration accumulates error

Integrating acceleration to velocity, and velocity to position, compounds any error in the acceleration signal:

- **Sensor bias** — a constant offset in the accelerometer reading integrates linearly into velocity error and quadratically into position error.
- **Attitude error** — if the rotation from body to NED is slightly wrong, the gravity subtraction is wrong, injecting a false acceleration that integrates without bound.
- **Noise** — even zero-mean noise produces a random-walk (Brownian) drift in position.

This is why the project does not claim a strapdown INS position. Instead `service/fusion/ekf_runner.py` fuses IMU measurements with GPS and attitude events in an EKF to bound the drift.

### The trapezoidal integration used for the IMU-speed metric

`service/metrics/metrics.py` computes a single engineering figure, `max_imu_speed_ms`, to give a rough velocity estimate from the raw IMU log. The gravity term is corrected on the Z axis before integrating:

```python title="service/metrics/metrics.py"
        acc_z = np.array([msg.get("AccZ", 0) for msg in imu_data]) + GRAVITY_MS2

        vel_x = integrate_velocity(acc_x, imu_times)
        vel_y = integrate_velocity(acc_y, imu_times)
        vel_z = integrate_velocity(acc_z, imu_times)

        imu_speed = np.sqrt(vel_x**2 + vel_y**2 + vel_z**2)
        metrics["max_imu_speed_ms"] = float(np.max(imu_speed))
```

`integrate_velocity` uses the trapezoidal rule, implemented in `service/common/integration.py`:

```python title="service/common/integration.py"
def trapz_step(val_prev: float, val_curr: float, dt: float) -> float:
    """One trapezoidal integration step over dt."""
    if dt <= 0:
        return 0.0
    return 0.5 * (val_prev + val_curr) * dt


def integrate_velocity(accel_array: np.ndarray, time_array: np.ndarray) -> np.ndarray:
    """Integrate acceleration over time with trapezoidal rule."""
    velocity = np.zeros_like(accel_array, dtype=float)
    for i in range(1, len(accel_array)):
        dt = float(time_array[i] - time_array[i - 1])
        if dt > 0:
            velocity[i] = velocity[i - 1] + trapz_step(
                float(accel_array[i - 1]), float(accel_array[i]), dt
            )
    return velocity
```

The result is the maximum 3-D speed magnitude over the flight — an **engineering display figure**, not a navigation-grade velocity. The Streamlit dashboard (`views/summary.py`) shows it as a stat card; the legacy Dash table in `drone_dashboard.py` labels it explicitly as `"IMU-derived Speed ... (trapezoidal integration)"` and the acceleration card as `"gravity-compensated"` so the method is visible to the user.

---

## Where to find each explanation in the repo

| Topic | File | What the comment explains |
|-------|------|---------------------------|
| Gimbal lock guard | `service/fusion/ekf_core.py` | Names the singularity; shows fallback branch |
| Specific force / gravity | `service/fusion/ekf_core.py` | Why `+= GRAVITY_MS2` is needed after body→NED rotation |
| Trapezoidal rule | `service/common/integration.py` | Docstrings on `trapz_step` and `integrate_velocity` |
| Gravity correction before integration | `service/metrics/metrics.py` | Single-axis Z correction before `integrate_velocity` |
| Coordinate frame (NED → ENU) | `drone_dashboard.py` | Comment on EKF trajectory source selection |
| Haversine formula | `service/geo/geodesy.py` | Great-circle distance on WGS-84 sphere |

---

## See also

- [Functionality](functionality.md) — how the EKF and metrics fit into the app.
- [Development](development.md) — layout of `service/`.

# Чому матиматика матиматюкається?

This page is about **where theory shows up in this project**: comments, short docstrings, and the structure of the formulas themselves. Below are two typical topics (quaternions / Euler / gimbal lock; errors from double integration of IMU data) plus pointers to specific files.

---

## Theoretical grounding in code: where to look

| Topic | Location in the repo |
|--------|------------------------|
| Coordinate transforms, Haversine, local frames | `service/geo/geodesy.py` |
| Trapezoidal integration of acceleration | `service/common/integration.py` |
| Body→NED orientation, rotation matrix from Euler angles | `service/fusion/orientation.py` |
| EKF state prediction, Euler kinematics, gravity in NED | `service/fusion/ekf_core.py` |
| Metrics: dynamic acceleration, IMU-derived speed integral | `service/metrics/metrics.py` |

Good practice: a **short comment next to the line that implements a formula** (what is being integrated, which frame, what the accelerometer actually measures) so the “why” survives refactoring.

---

## Euler angles, quaternions, and gimbal lock

**Idea.** Body attitude can be parameterized with Euler angles (roll, pitch, yaw). In a common ZYX formulation, the rates of those angles depend on **tangent** and **cosine of pitch** in denominators: when the **tangent blows up** or **cosine goes to zero** (e.g. pitch ≈ ±90°), you get a **singularity** known as **gimbal lock**—one degree of freedom becomes ill-conditioned and angular rates are poorly defined.

**Quaternions** (unit quaternions on S³) represent rotations without that class of singularity in the same parameterization; navigation filters often use them specifically to **avoid gimbal lock** over the full tilt range.

**What Lift & Drone does.** In the EKF, attitude is stored as **Euler angles** in the state vector (`roll`, `pitch`, `yaw`), and body→navigation rotation uses an **Euler-based matrix** (`euler_to_rotation_matrix` in `service/fusion/orientation.py`). State prediction explicitly handles **pitch singularity**: when **the absolute value of cos(pitch)** is very small, a **fallback** (simplified) angle update is used—this is documented directly in code:

```python title="service/fusion/ekf_core.py (excerpt)"
        # Euler kinematics: convert body rates (p, q, r) to Euler rates
        if abs(cp) > 1e-6:  # Prevent gimbal lock singularity
            roll += (p + q * sr * tp + r * cr * tp) * dt
            pitch += (q * cr - r * sr) * dt
            yaw += (q * sr / cp + r * cr / cp) * dt
        else:
            # Fallback if pitched near 90 degrees
            roll += p * dt
            pitch += q * dt
            yaw += r * dt
```

So **the theory is in the comments**: gimbal lock is named and the nature of the guard is clear. Moving the filter state to **quaternions** would be a **different design** (different state size and equations); this codebase documents a **singularity workaround for Euler angles**, not a quaternion state.

---

## Double integration of IMU data: where errors come from

**Idea.** An accelerometer measures **specific force**: at rest it reads roughly “−g” along the vertical in the body frame. To get **acceleration in an inertial/navigation frame** you need attitude and a correct **gravity subtraction**—otherwise bogus acceleration integrates into velocity and **drift** grows over time.

**Double integration** (acceleration → velocity → position) on a **bare IMU without aiding** accumulates:

- **Bias** and noise: velocity error typically grows with time; position error grows faster still.
- **Attitude errors** mix axes, so gravity compensation **drifts**.

That is why real systems almost always **aid** IMU position with GPS / baro / magnetometers (here: an EKF with IMU+GPS+ATT events in `service/fusion/ekf_runner.py`).

**What Lift & Drone does for `max_imu_speed_ms`.** In `compute_metrics`, IMU speed uses **trapezoidal integration** of per-axis accelerations after adding gravity on the vertical axis for the velocity integral—see `integrate_velocity` and the module docstring in `service/common/integration.py`. That is an **engineering display metric**, not a claimed high-grade INS position solution. Comments in `ekf_core.py` explain **specific force**, **g**, and NED:

```python title="service/fusion/ekf_core.py (excerpt)"
    # Convert raw acceleration to dynamic acceleration in NED.
    # In NED, gravity is a downward vector [0, 0, g].
    # Accelerometer measures specific force: a_meas = a_true - g_vector.
    # Therefore, a_true = a_meas + g_vector.
    acc_nav_dyn = acc_nav.copy()
    acc_nav_dyn[2] += GRAVITY_MS2
```

That is **mathematical explanation in comments**: what the measurement means and how we move to “dynamic” acceleration in the navigation frame.

---

## Other “why this formula” notes in the repo

- **Haversine** in `service/geo/geodesy.py` — great-circle distance between two WGS84 points; the implementation matches the standard spherical formula.
- **Trapezoid** in `trapz_step` — explicit average of two neighboring acceleration samples over a time step `dt`.

When you add new transforms, briefly document the **coordinate system** (NED vs ENU, which way is “up”), **units**, and **what the sensor actually outputs**—then a page like this stays useful for future readers of the repository.

---

## See also

- [Functionality](functionality.md) — how the EKF and metrics fit the app.
- [Development](development.md) — layout of `service/`.

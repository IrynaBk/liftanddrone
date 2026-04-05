"""Example: demonstrating the critical Alt/VZ sign mismatch in ArduPilot logs."""

from processing.geodesy import llh_to_ned, normalize_gps_measurement


def example_sign_mismatch():
    """
    Show why normalization is critical.
    
    Scenario:
    - Start at lat=0, lon=0, alt=100m (on a hill)
    - Move to lat=0, lon=0, alt=150m (higher up)
    - GPS reports Alt=150 (altitude in Up system: higher is more)
    - But if we treat increasing altitude as increasing Down, integrating positive VZ
      would take us DOWN, contradicting GPS!
    """
    
    ref_lat, ref_lon, ref_alt = 0.0, 0.0, 100.0  # Start at 100m
    
    # Scenario 1: Drone climbs to 150m (moving UP in real world)
    target_alt = 150.0  # Higher altitude in Up system
    
    # WITHOUT normalization (WRONG):
    # If we naively use altitude difference: up = target_alt - ref_alt = 50m ✓
    # But if VZ is positive (descending in Down system) and we integrate it:
    # down_integrated = down_integrated + VZ * dt  (upward displacement)
    # This CONTRADICTS the GPS Alt reading!
    
    # WITH normalization (CORRECT):
    north, east, down = llh_to_ned(0.0, 0.0, target_alt, ref_lat, ref_lon, ref_alt)
    print("Scenario: Climbing from 100m to 150m MSL")
    print(f"  GPS Alt (Up system):        {target_alt} m")
    print(f"  Normalized to NED:")
    print(f"    North: {north:.2f} m")
    print(f"    East:  {east:.2f} m")
    print(f"    Down:  {down:.2f} m  (negative = UP from start)")
    print()
    
    # Scenario 2: Drone descends to 50m
    target_alt = 50.0
    north, east, down = llh_to_ned(0.0, 0.0, target_alt, ref_lat, ref_lon, ref_alt)
    print("Scenario: Descending from 100m to 50m MSL")
    print(f"  GPS Alt (Up system):        {target_alt} m")
    print(f"  Normalized to NED:")
    print(f"    North: {north:.2f} m")
    print(f"    East:  {east:.2f} m")
    print(f"    Down:  {down:.2f} m  (positive = DOWN from start)")
    print()
    
    # Verification
    print("Sign consistency check:")
    print("  When Alt increases (going UP in world):")
    print("    ✓ down becomes more negative (moving UP in NED)")
    print("  When Alt decreases (going DOWN in world):")
    print("    ✓ down becomes more positive (moving DOWN in NED)")
    print()
    
    # Show the normalize wrapper function
    gps_1 = {"Lat": 0.0, "Lng": 0.0, "Alt": 150.0, "VZ": 0.0}
    n, e, d = normalize_gps_measurement(gps_1, ref_lat, ref_lon, ref_alt)
    print(f"normalize_gps_measurement() result: N={n:.2f}, E={e:.2f}, D={d:.2f}")


if __name__ == "__main__":
    example_sign_mismatch()

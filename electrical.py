import math


def analyze_dc(voltage_v, resistance_ohm):
    """Return current (A) and power (W) for a DC voltage and resistance."""
    for name, value in (("voltage_v", voltage_v), ("resistance_ohm", resistance_ohm)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")

    if resistance_ohm <= 0:
        raise ValueError("resistance_ohm must be greater than zero")

    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


def _read_number(prompt):
    while True:
        try:
            value = float(input(prompt))
        except ValueError:
            print("Please enter a valid number.")
            continue

        if math.isfinite(value):
            return value
        print("Please enter a finite number.")


def main():
    print("DC Circuit Calculator")
    voltage_v = _read_number("Voltage (V): ")

    while True:
        resistance_ohm = _read_number("Resistance (ohms): ")
        try:
            result = analyze_dc(voltage_v, resistance_ohm)
        except ValueError as error:
            print(f"Invalid input: {error}")
            continue
        break

    print(f"Current: {result['current_a']:.3f} A")
    print(f"Power: {result['power_w']:.3f} W")


if __name__ == "__main__":
    main()
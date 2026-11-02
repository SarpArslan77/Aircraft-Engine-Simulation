
#* sim_model/quantize_floats.py

def quantize_floats(
        val: float,
        int_bit_width: int,
        fractional_bit_width: int,
        signed: bool
) -> int:
    """
    Quantizes and saturates a floating-point value into a fixed-point integer representation.

    Converts a continuous floating-point scalar into a scaled integer by shifting the binary
    radix point by fractional_bit_width bits, rounding to the nearest even integer, and
    applying two's-complement saturation clamping to prevent arithmetic overflow wrap-around.

    Mathematical Formulations:
    1. Scaled Value:
    scaled = val * 2^(fractional_bit_width)
    2. Rounded Value:
    rounded = round(scaled)
    3. Saturation Bounds:
    If signed:
        min_int = -2^(total_bit_width - 1)
        max_int = 2^(total_bit_width - 1) - 1
    If unsigned:
        min_int = 0
        max_int = 2^(total_bit_width) - 1
    4. Saturated Output:
    result = max(min_int, min(max_int, rounded))

    Args:
        val (float): Physical floating-point continuous scalar to quantize.
        int_bit_width (int): Bit width allocated for integer magnitude (including sign bit if signed).
        fractional_bit_width (int): Bit width allocated for fractional resolution.
        signed (bool): True for signed two's-complement bounds, False for unsigned bounds.

    Returns:
        int: Quantized and saturated integer representing the fixed-point scalar in raw LSBs.
    """
    # Scales the value by shifting the binary point.
    scaled_val: float = val * (1 << fractional_bit_width)

    # Rounds to the nearest integer.
    #?  round(): Rounds to the nearest even.
    rounded_val: int = round(number = scaled_val)

    # Calculates the bounds and saturates the integer.
    total_bit_width: int = int_bit_width + fractional_bit_width

    if signed:
        min_int: int = -(1 << (total_bit_width - 1))
        max_int: int = (1 << (total_bit_width - 1)) - 1
    else:
        min_int: int = 0
        max_int: int = (1 << total_bit_width) - 1

    saturated_val: int = max(min_int, min(max_int, rounded_val))

    return saturated_val
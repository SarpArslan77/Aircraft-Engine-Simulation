
#* quantize_floats.py

def quantize_floats(
        val: float,
        int_bit_width: int,
        fractional_bit_width: int,
        signed: bool
) -> int:
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
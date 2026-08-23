
//* calculate_derivatives.v

`timescale 1ns / 1ps

//* ======= Derivative Calculation =======
module calculate_derivatives #(
    // ------- Parameters. -------
    // Data Representation.
    parameter signed INTEGER_BIT_WIDTH = 16,
    parameter signed FRACTIONAL_BIT_WIDTH = 16,

    // Time Constants (Intertia).
    parameter signed [31:0] PRE_CALCULATED_ROTOR_INTERTIAL_TIME_CONST = 0,
    parameter signed [31:0] PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST = 0,
    parameter signed [31:0] PRE_CALCULATED_THERMAL_TIME_CONST = 0
)(
    // ------- Inputs. -------
    // Currents.
    input wire signed [31:0] current_rotational_speed, current_compressor_pressure, current_exhaust_gas_temperature,

    // Targets.
    input wire signed [31:0] target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature,

    // ------- Outputs. -------
    output wire signed [31:0] d_rotational_speed, d_compressor_pressure, d_exhaust_gas_temperature
);
    // ------- Local Parameters. -------
    localparam TOTAL_BIT_WIDTH = INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;

    // ------- Wires. -------
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] rotational_speed_mult = PRE_CALCULATED_ROTOR_INTERTIAL_TIME_CONST * (target_rotational_speed - current_rotational_speed);
    assign d_rotational_speed = (rotational_speed_mult >>> FRACTIONAL_BIT_WIDTH);

    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] compressor_pressure_mult = PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST * (target_compressor_pressure - current_compressor_pressure);
    assign d_compressor_pressure = (compressor_pressure_mult >>> FRACTIONAL_BIT_WIDTH);

    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] exhaust_gas_temperature_mult = PRE_CALCULATED_THERMAL_TIME_CONST * (target_exhaust_gas_temperature - current_exhaust_gas_temperature);
    assign d_exhaust_gas_temperature = (exhaust_gas_temperature_mult >>> FRACTIONAL_BIT_WIDTH);

endmodule
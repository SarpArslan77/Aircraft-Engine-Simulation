
//* calculate_target_values.v

`timescale 1ns / 1ps

//* ======= Target Calculations =======
module calculate_target_values #(
    // ------- Parameters. -------
    // Data Representation.
    parameter INTEGER_BIT_WIDTH = 16,
    parameter FRACTIONAL_BIT_WIDTH = 16,

    // Ambient Conditions.
    parameter signed [31:0] AMBIENT_PRESSURE = 0,
    parameter signed [31:0] AMBIENT_TEMPERATURE = 0
)(
    // ------- Inputs. -------
    // Dependents.
    input wire signed [31:0] current_fuel_flow, current_rotational_speed,

    // Gains.
    input wire signed [31:0] speed_gain_coeff,
    input wire signed [31:0] compressor_pressure_gain,
    input wire signed [31:0] combustion_heat_gain,
    input wire signed [31:0] mass_overflow_cooling_gain,

    // ------- Outputs. -------
    output wire signed [31:0] target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature
);
    // Local Parameters.
    localparam TOTAL_BIT_WIDTH = INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;

    // ------- Wires. -------
    // Intermediate 64-bit Multiplications.
    // Rotational Speed.
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] speed_mult = current_fuel_flow * speed_gain_coeff;
    
    assign target_rotational_speed = (speed_mult >>> FRACTIONAL_BIT_WIDTH);

    // Compressor Pressure.
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] speed_squared = current_rotational_speed * current_rotational_speed;
    wire signed [TOTAL_BIT_WIDTH-1:0] speed_squared_q32 = speed_squared >>> FRACTIONAL_BIT_WIDTH;
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] pressure_mult = speed_squared_q32 * compressor_pressure_gain;

    assign target_compressor_pressure = (AMBIENT_PRESSURE + (pressure_mult >>> FRACTIONAL_BIT_WIDTH));

    // Exhaust Gas Temperature.
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] heat_mult = combustion_heat_gain * current_fuel_flow;
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] cooling_mult = mass_overflow_cooling_gain * current_rotational_speed;
    
    assign target_exhaust_gas_temperature = (AMBIENT_TEMPERATURE + (heat_mult >>> FRACTIONAL_BIT_WIDTH) - (cooling_mult >>> FRACTIONAL_BIT_WIDTH));

endmodule
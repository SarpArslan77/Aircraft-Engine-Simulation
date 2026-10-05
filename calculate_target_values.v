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
    // System Signals.
    input wire clk, rst,

    // Dependents.
    input wire signed [31:0] current_fuel_flow, 
    input wire signed [31:0] current_rotational_speed,

    // Gains.
    input wire signed [31:0] speed_gain_coeff,
    input wire signed [31:0] compressor_pressure_gain,
    input wire signed [31:0] combustion_heat_gain,
    input wire signed [31:0] mass_overflow_cooling_gain,

    // ------- Outputs. -------
    output wire signed [31:0] target_rotational_speed, 
    output wire signed [31:0] target_compressor_pressure, 
    output wire signed [31:0] target_exhaust_gas_temperature
);
    // ------- Local Parameters. -------
    localparam TOTAL_BIT_WIDTH = INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;
    localparam MULTIPLICATION_BIT_WIDTH = TOTAL_BIT_WIDTH * 2;

    // ------- Wires. -------
    // Rotational Speed (RS).
    assign target_rotational_speed = (speed_mult_r2 >>> FRACTIONAL_BIT_WIDTH);

    // Compressor Pressure (CP).
    wire signed [TOTAL_BIT_WIDTH-1:0] speed_squared_q32 = speed_squared_r >>> FRACTIONAL_BIT_WIDTH;

    assign target_compressor_pressure = (AMBIENT_PRESSURE + (pressure_mult_r >>> FRACTIONAL_BIT_WIDTH));

    // Exhaust Gas Temperature (EGT).
    assign target_exhaust_gas_temperature = (AMBIENT_TEMPERATURE + (heat_mult_r2 >>> FRACTIONAL_BIT_WIDTH) - (cooling_mult_r2 >>> FRACTIONAL_BIT_WIDTH));

    // ------- Registers. -------
    // RS.
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] speed_mult_r1;
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] speed_mult_r2;

    // CP.
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] speed_squared_r;
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] pressure_mult_r;

    // EGT.
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] heat_mult_r1;
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] heat_mult_r2;
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] cooling_mult_r1;
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] cooling_mult_r2;

    // ------- Sequential Logic. -------
    always @(posedge clk) begin
        if (rst) begin
            speed_mult_r1 <= 0;
            speed_mult_r2 <= 0;

            speed_squared_r <= 0;
            pressure_mult_r <= 0;

            heat_mult_r1 <= 0;
            heat_mult_r2 <= 0;
            cooling_mult_r1 <= 0;
            cooling_mult_r2 <= 0;
        end
        else begin
            // ------- Cycle 1: First Multiplications. -------
            // RS.
            speed_mult_r1 <= current_fuel_flow * speed_gain_coeff;

            // CP.
            speed_squared_r <= current_rotational_speed * current_rotational_speed;

            // EGT.
            heat_mult_r1 <= combustion_heat_gain * current_fuel_flow;
            cooling_mult_r1 <= mass_overflow_cooling_gain * current_rotational_speed;

            // ------- Cycle 2: Secondary Multiplications & Delay Balancing. -------
            // RS.
            speed_mult_r2 <= speed_mult_r1;

            // CP.
            pressure_mult_r <= speed_squared_q32 * compressor_pressure_gain;

            // EGT.
            heat_mult_r2 <= heat_mult_r1;
            cooling_mult_r2 <= cooling_mult_r1;
        end
    end

endmodule
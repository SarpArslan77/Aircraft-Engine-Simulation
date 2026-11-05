
//* rtl/calculate_target_values.v

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
    input wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] current_fuel_flow,
    input wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] current_rotational_speed,

    // Gains.
    input wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] speed_gain_coeff,
    input wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] compressor_pressure_gain,
    input wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] combustion_heat_gain,
    input wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] mass_overflow_cooling_gain,

    // ------- Outputs. -------
    output wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] target_rotational_speed,
    output wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] target_compressor_pressure,
    output wire signed [(INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] target_exhaust_gas_temperature
);
    // ------- Local Parameters. -------
    localparam TOTAL_BIT_WIDTH = INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;
    localparam MULTIPLICATION_BIT_WIDTH = TOTAL_BIT_WIDTH * 2;

    // ------- Wires. -------
    // Rotational Speed (RS).
    wire signed [MULTIPLICATION_BIT_WIDTH-1:0] speed_mult_shifted = (speed_mult_q2 >>> FRACTIONAL_BIT_WIDTH);

    assign target_rotational_speed = speed_mult_shifted[TOTAL_BIT_WIDTH-1:0];

    // Compressor Pressure (CP).
    wire signed [MULTIPLICATION_BIT_WIDTH-1:0] speed_squared_shifted = (speed_squared_q >>> FRACTIONAL_BIT_WIDTH);
    wire signed [TOTAL_BIT_WIDTH-1:0] speed_squared_q32 = speed_squared_shifted[TOTAL_BIT_WIDTH-1:0];

    wire signed [MULTIPLICATION_BIT_WIDTH-1:0] pressure_mult_shifted = (pressure_mult_q >>> FRACTIONAL_BIT_WIDTH);
    wire signed [TOTAL_BIT_WIDTH-1:0] pressure_mult_q32 = pressure_mult_shifted[TOTAL_BIT_WIDTH-1:0];

    assign target_compressor_pressure = (AMBIENT_PRESSURE + pressure_mult_q32);

    // Exhaust Gas Temperature (EGT).
    wire signed [MULTIPLICATION_BIT_WIDTH-1:0] heat_mult_shifted = (heat_mult_q2 >>> FRACTIONAL_BIT_WIDTH);
    wire signed [TOTAL_BIT_WIDTH-1:0] heat_mult_q32 = heat_mult_shifted[TOTAL_BIT_WIDTH-1:0];

    wire signed [MULTIPLICATION_BIT_WIDTH-1:0] cooling_mult_shifted = (cooling_mult_q2 >>> FRACTIONAL_BIT_WIDTH);
    wire signed [TOTAL_BIT_WIDTH-1:0] cooling_mult_q32 = cooling_mult_shifted[TOTAL_BIT_WIDTH-1:0];

    assign target_exhaust_gas_temperature = (AMBIENT_TEMPERATURE + heat_mult_q32 - cooling_mult_q32);

    // Sinks discarded upper 32 bits of 64-bit intermediate products.
    wire _unused_targets = &{1'b0,
        speed_mult_shifted[MULTIPLICATION_BIT_WIDTH-1:TOTAL_BIT_WIDTH],
        speed_squared_shifted[MULTIPLICATION_BIT_WIDTH-1:TOTAL_BIT_WIDTH],
        pressure_mult_shifted[MULTIPLICATION_BIT_WIDTH-1:TOTAL_BIT_WIDTH],
        heat_mult_shifted[MULTIPLICATION_BIT_WIDTH-1:TOTAL_BIT_WIDTH],
        cooling_mult_shifted[MULTIPLICATION_BIT_WIDTH-1:TOTAL_BIT_WIDTH]
    };

    // ------- Registers. -------
    // RS.
    (* use_dsp = "no" *)  reg signed [MULTIPLICATION_BIT_WIDTH-1:0] speed_mult_q1;
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] speed_mult_q2;

    // CP.
    (* use_dsp = "yes" *)  reg signed [MULTIPLICATION_BIT_WIDTH-1:0] speed_squared_q;
    (* use_dsp = "no" *)  reg signed [MULTIPLICATION_BIT_WIDTH-1:0] pressure_mult_q;

    // EGT.
    (* use_dsp = "no" *)  reg signed [MULTIPLICATION_BIT_WIDTH-1:0] heat_mult_q1;
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] heat_mult_q2;
    (* use_dsp = "no" *)  reg signed [MULTIPLICATION_BIT_WIDTH-1:0] cooling_mult_q1;
    reg signed [MULTIPLICATION_BIT_WIDTH-1:0] cooling_mult_q2;

    // ------- Sequential Logic. -------
    always @(posedge clk) begin
        if (rst) begin
            speed_mult_q1 <= 0;
            speed_mult_q2 <= 0;

            speed_squared_q <= 0;
            pressure_mult_q <= 0;

            heat_mult_q1 <= 0;
            heat_mult_q2 <= 0;
            cooling_mult_q1 <= 0;
            cooling_mult_q2 <= 0;
        end
        else begin
            // ------- Cycle 1: First Multiplications. -------
            // RS.
            speed_mult_q1 <= current_fuel_flow * speed_gain_coeff;

            // CP.
            speed_squared_q <= current_rotational_speed * current_rotational_speed;

            // EGT.
            heat_mult_q1 <= current_fuel_flow * combustion_heat_gain;
            cooling_mult_q1 <= current_rotational_speed * mass_overflow_cooling_gain;

            // ------- Cycle 2: Secondary Multiplications & Delay Balancing. -------
            // RS.
            speed_mult_q2 <= speed_mult_q1;

            // CP.
            pressure_mult_q <= speed_squared_q32 * compressor_pressure_gain;

            // EGT.
            heat_mult_q2 <= heat_mult_q1;
            cooling_mult_q2 <= cooling_mult_q1;
        end
    end
endmodule


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
    parameter signed [31:0] AMBIENT_TEMPERATURE = 0,

    // Gains.
    parameter signed [31:0] SPEED_GAIN_COEFF = 0,
    parameter signed [31:0] COMPRESSOR_PRESSURE_GAIN = 0,
    parameter signed [31:0] COMBUSTION_HEAT_GAIN = 0,
    parameter signed [31:0] MASS_OVERFLOW_COOLING_GAIN = 0
)(
    // ------- Inputs. -------
    // System Signals.
    input wire clk, rst

    // Dependents.
    input wire signed [31:0] current_fuel_flow, current_rotational_speed,

    // ------- Outputs. -------
    // Target States.
    output reg signed [31:0] target_rotational_speed, target_compressor_pressure, target_exhaust_gas_temperature
);
    // Local Parameters.
    localparam TOTAL_BIT_WIDTH = INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;

    // ------- Wires. -------
    // Intermediate 64-bit Multiplications.
    // Rotational Speed.
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] speed_mult = current_fuel_flow * SPEED_GAIN_COEFF;

    // Compressor Pressure.
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] speed_squared = current_rotational_speed * current_rotational_speed;
    wire signed [TOTAL_BIT_WIDTH-1:0] speed_squared_q32 = speed_square >>> FRACTIONAL_BIT_WIDTH;
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] pressure_mult = speed_squared_q32 * COMPRESSOR_PRESSURE_GAIN;

    // Exhaust Gas Temperature.
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] heat_mult = COMBUSTION_HEAT_GAIN * current_fuel_flow;
    wire signed [(2*TOTAL_BIT_WIDTH)-1:0] cooling_mult = MASS_OVERFLOW_COOLING_GAIN * current_rotational_speed;

    // ------- Sequential Logic Block. -------
    always @(posedge clk) begin
        if (rst) begin
            target_rotational_speed <= 0;
            target_compressor_pressure <= 0;
            target_exhaust_gas_temperature <= 0;
        end
        else begin
            // Updates the target values with 1-cycle latency.
            target_rotational_speed <= (speed_mult >>> FRACTIONAL_BIT_WIDTH);

            target_compressor_pressure <= (AMBIENT_PRESSURE + (pressure_mult >>> FRACTIONAL_BIT_WIDTH));

            target_exhaust_gas_temperature <= (AMBIENT_TEMPERATURE + (heat_mult >>> FRACTIONAL_BIT_WIDTH) - (cooling_mult >>> FRACTIONAL_BIT_WIDTH));
        end
    end

endmodule
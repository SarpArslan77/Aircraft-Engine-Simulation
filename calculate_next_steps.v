
//* calculate_next_steps.v

`timescale 1ns / 1ps

//* ======= Next Step Calculation =======
module calculate_next_steps #(
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

    // Currents.
    input wire signed [31:0] current_rotational_speed, 
    input wire signed [31:0] current_compressor_pressure, 
    input wire signed [31:0] current_exhaust_gas_temperature,

    // Derivatives.
    input wire signed [31:0] d_rotational_speed, 
    input wire signed [31:0] d_compressor_pressure, 
    input wire signed [31:0] d_exhaust_gas_temperature,

    // ------- Outputs. -------
    output wire signed [31:0] next_rotational_speed, 
    output wire signed [31:0] next_compressor_pressure, 
    output wire signed [31:0] next_exhaust_gas_temperature
);
    // ------- Local Parameters. -------
    localparam TOTAL_BIT_WIDTH = INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;

    // ------- Wires. -------
    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_rotational_speed = (current_rotational_speed + (d_rotational_speed >>> FRACTIONAL_BIT_WIDTH));
    assign next_rotational_speed = (calculated_rotational_speed < 0) ? 0 : calculated_rotational_speed;

    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_compressor_pressure = (current_compressor_pressure + (d_compressor_pressure >>> FRACTIONAL_BIT_WIDTH));
    assign next_compressor_pressure = (calculated_compressor_pressure < AMBIENT_PRESSURE) ? AMBIENT_PRESSURE : calculated_compressor_pressure;
    
    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_exhaust_gas_temperature = (current_exhaust_gas_temperature + (d_exhaust_gas_temperature >>> FRACTIONAL_BIT_WIDTH));
    assign next_exhaust_gas_temperature = (calculated_exhaust_gas_temperature < AMBIENT_TEMPERATURE) ? AMBIENT_TEMPERATURE : calculated_exhaust_gas_temperature;

endmodule
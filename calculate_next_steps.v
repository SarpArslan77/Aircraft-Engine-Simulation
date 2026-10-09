
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

    // Maximum Possible Numbers.
    localparam MAX_ROTATIONAL_SPEED = (32'b1 << (TOTAL_BIT_WIDTH-1)) - 1;
    localparam MAX_COMPRESSOR_PRESSURE = (32'b1 << (TOTAL_BIT_WIDTH-1)) - 1;
    localparam MAX_EXHAUST_GAS_TEMPERATURE = (32'b1 << (TOTAL_BIT_WIDTH-1)) - 1;

    //* ======= Wires. =======
    // ------- Rotational Speed. -------
    wire signed [TOTAL_BIT_WIDTH-1:0] shifted_d_rotational_speed = d_rotational_speed >>> FRACTIONAL_BIT_WIDTH;
    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_rotational_speed = current_rotational_speed + shifted_d_rotational_speed;

    // Positive Overflow Detection.
    wire is_pos_overflow_detected_rotational_speed = (~current_rotational_speed[TOTAL_BIT_WIDTH-1] & ~shifted_d_rotational_speed[TOTAL_BIT_WIDTH-1] & calculated_rotational_speed[TOTAL_BIT_WIDTH-1]); // Pos + Pos = Neg.
    wire signed [TOTAL_BIT_WIDTH-1:0] pos_saturated_rotational_speed = is_pos_overflow_detected_rotational_speed ? MAX_ROTATIONAL_SPEED : calculated_rotational_speed;

    // Negative Overflow Detection.    
    assign next_rotational_speed = (pos_saturated_rotational_speed[TOTAL_BIT_WIDTH-1]) ? 0 : pos_saturated_rotational_speed;

    // ------- Compressor Pressure. -------
    wire signed [TOTAL_BIT_WIDTH-1:0] shifted_d_compressor_pressure = d_compressor_pressure >>> FRACTIONAL_BIT_WIDTH;
    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_compressor_pressure = current_compressor_pressure + shifted_d_compressor_pressure;

    wire is_pos_overflow_detected_compressor_pressure = (~current_compressor_pressure[TOTAL_BIT_WIDTH-1] & ~shifted_d_compressor_pressure[TOTAL_BIT_WIDTH-1] & calculated_compressor_pressure[TOTAL_BIT_WIDTH-1]); // Pos + Pos = Neg.
    wire signed [TOTAL_BIT_WIDTH-1:0] pos_saturated_compressor_pressure = is_pos_overflow_detected_compressor_pressure ? MAX_COMPRESSOR_PRESSURE : calculated_compressor_pressure;

    assign next_compressor_pressure = (pos_saturated_compressor_pressure < AMBIENT_PRESSURE) ? AMBIENT_PRESSURE : pos_saturated_compressor_pressure;

    // ------- Exhaust Gas Temperature. -------
    wire signed [TOTAL_BIT_WIDTH-1:0] shifted_d_exhaust_gas_temperature = d_exhaust_gas_temperature >>> FRACTIONAL_BIT_WIDTH;
    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_exhaust_gas_temperature = current_exhaust_gas_temperature + shifted_d_exhaust_gas_temperature;

    wire is_pos_overflow_detected_exhaust_gas_temperature = (~current_exhaust_gas_temperature[TOTAL_BIT_WIDTH-1] & ~shifted_d_exhaust_gas_temperature[TOTAL_BIT_WIDTH-1] & calculated_exhaust_gas_temperature[TOTAL_BIT_WIDTH-1]); // Pos + Pos = Neg.
    wire signed [TOTAL_BIT_WIDTH-1:0] pos_saturated_exhaust_gas_temperature = is_pos_overflow_detected_exhaust_gas_temperature ? MAX_EXHAUST_GAS_TEMPERATURE : calculated_exhaust_gas_temperature;

    assign next_exhaust_gas_temperature = (pos_saturated_exhaust_gas_temperature < AMBIENT_TEMPERATURE) ? AMBIENT_TEMPERATURE : pos_saturated_exhaust_gas_temperature;

endmodule
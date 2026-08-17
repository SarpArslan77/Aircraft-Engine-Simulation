
//* calculate_next_step.v

`timescale 1ns / 1ps

//* ======= Next Step Calculation =======
module calculate_next_step #(
    // ------- Parameters. -------
    // Data Representation. 
    parameter INTEGER_BIT_WIDTH = 16,
    parameter FRACTIONAL_BIT_WIDTH = 16,

    // Ambient Conditions.
    parameter AMBIENT_PRESSURE = 0,
    parameter AMBIENT_TEMPERATURE = 0
)(
    // ------- Inputs. -------
    // System Signals.
    input wire clk, rst,

    // Currents.
    input wire signed [31:0] current_rotational_speed, current_compressor_pressure, current_exhaust_gas_temperature,

    // Derivatives.
    input wire signed [31:0] d_rotational_speed, d_compressor_pressure, d_exhaust_gas_temperature,

    // ------- Outputs. -------
    output reg signed [31:0] next_rotational_speed, next_compressor_pressure, next_exhaust_gas_temperature
);
    // ------- Local Parameters. -------
    localparam TOTAL_BIT_WIDTH = INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;

    // ------- Wires. -------
    // Intermediate Additions.
    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_rotational_speed = (current_rotational_speed + (d_rotational_speed >>> FRACTIONAL_BIT_WIDTH));

    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_compressor_pressure = (current_compressor_pressure + (d_compressor_pressure >>> FRACTIONAL_BIT_WIDTH));
    
    wire signed [TOTAL_BIT_WIDTH-1:0] calculated_exhaust_gas_temperature = (current_exhaust_gas_temperature + (d_exhaust_gas_temperature >>> FRACTIONAL_BIT_WIDTH));

    // ------- Sequential Logic. -------
    always @(posedge clk) begin
        if (rst) begin
            next_rotational_speed <= 0;
            next_compressor_pressure <= AMBIENT_PRESSURE;
            next_exhaust_gas_temperature <= AMBIENT_TEMPERATURE;
        end
        else begin
            // Assigns the next states with 1-cycle delay.
            next_rotational_speed <= (calculated_rotational_speed < 0) ? 0 : calculated_rotational_speed;

            next_compressor_pressure <= (calculated_compressor_pressure < AMBIENT_PRESSURE) ? AMBIENT_PRESSURE : calculated_compressor_pressure;

            next_exhaust_gas_temperature <= (calculated_exhaust_gas_temperature < AMBIENT_TEMPERATURE) ? AMBIENT_TEMPERATURE : calculated_exhaust_gas_temperature;
        end
    end

endmodule

//* rtl/calculate_derivatives.v

`timescale 1ns / 1ps

//* ======= Derivative Calculation =======
module calculate_derivatives #(
    // ------- Parameters. -------
    // Data Representation.
    parameter signed INT_BIT_WIDTH = 16,
    parameter signed FRACTIONAL_BIT_WIDTH = 16,

    // Time Constants (Intertia).
    parameter signed [31:0] PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST = 0,
    parameter signed [31:0] PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST = 0,
    parameter signed [31:0] PRE_CALCULATED_THERMAL_TIME_CONST = 0
)(
    // ------- Inputs. -------
    // System Signals.
    input wire clk, rst,

    // Currents.
    input wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] current_rotational_speed,
    input wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] current_compressor_pressure,
    input wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] current_exhaust_gas_temperature,

    // Targets.
    input wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] target_rotational_speed,
    input wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] target_compressor_pressure,
    input wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] target_exhaust_gas_temperature,

    // ------- Outputs. -------
    output wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] d_rotational_speed,
    output wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] d_compressor_pressure,
    output wire signed [(INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH)-1:0] d_exhaust_gas_temperature
);
    // ------- Local Parameters. -------
    localparam TOTAL_BIT_WIDTH = INT_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;
    localparam MULTIPLICATION_BIT_WIDTH = TOTAL_BIT_WIDTH * 2;

    // ------- Registers. -------
    (* use_dsp = "no" *) reg signed [MULTIPLICATION_BIT_WIDTH-1:0] rotational_speed_mult_q;

    (* use_dsp = "no" *) reg signed [MULTIPLICATION_BIT_WIDTH-1:0] compressor_pressure_mult_q;

    (* use_dsp = "no" *) reg signed [MULTIPLICATION_BIT_WIDTH-1:0] exhaust_gas_temperature_mult_q;

    // ------- Wires. -------
    // Rotational Speed (RS).
    wire signed [TOTAL_BIT_WIDTH-1:0] rotational_speed_delta = target_rotational_speed - current_rotational_speed;
    wire signed [MULTIPLICATION_BIT_WIDTH-1:0] d_rotational_speed_shifted = rotational_speed_mult_q >>> FRACTIONAL_BIT_WIDTH;
    assign d_rotational_speed = d_rotational_speed_shifted[TOTAL_BIT_WIDTH-1:0];

    // Compressor Pressure (CP).
    wire signed [TOTAL_BIT_WIDTH-1:0] compressor_pressure_delta = target_compressor_pressure - current_compressor_pressure;
    wire signed [MULTIPLICATION_BIT_WIDTH-1:0] d_compressor_pressure_shifted = compressor_pressure_mult_q >>> FRACTIONAL_BIT_WIDTH;
    assign d_compressor_pressure = d_compressor_pressure_shifted[TOTAL_BIT_WIDTH-1:0];

    // Exhaust Gas Temperature (EGT).
    wire signed [TOTAL_BIT_WIDTH-1:0] exhaust_gas_temperature_delta = target_exhaust_gas_temperature - current_exhaust_gas_temperature;
    wire signed [MULTIPLICATION_BIT_WIDTH-1:0] d_exhaust_gas_temperature_shifted = exhaust_gas_temperature_mult_q >>> FRACTIONAL_BIT_WIDTH;
    assign d_exhaust_gas_temperature = d_exhaust_gas_temperature_shifted[TOTAL_BIT_WIDTH-1:0];

    // Sinks discarded upper 32 bits of the 64-bit intermediate shifts.
    wire _unused_derivatives = &{1'b0,
        d_rotational_speed_shifted[MULTIPLICATION_BIT_WIDTH-1:TOTAL_BIT_WIDTH],
        d_compressor_pressure_shifted[MULTIPLICATION_BIT_WIDTH-1:TOTAL_BIT_WIDTH],
        d_exhaust_gas_temperature_shifted[MULTIPLICATION_BIT_WIDTH-1:TOTAL_BIT_WIDTH]
    };

    // ------- Sequential Logic. -------
    always @(posedge clk) begin
        if (rst) begin
            rotational_speed_mult_q <= 0;

            compressor_pressure_mult_q <= 0;

            exhaust_gas_temperature_mult_q <= 0;
        end
        else begin
            rotational_speed_mult_q <= PRE_CALCULATED_ROTOR_INERTIAL_TIME_CONST * rotational_speed_delta;

            compressor_pressure_mult_q <= PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST * compressor_pressure_delta;

            exhaust_gas_temperature_mult_q <= PRE_CALCULATED_THERMAL_TIME_CONST * exhaust_gas_temperature_delta;
        end
    end
endmodule

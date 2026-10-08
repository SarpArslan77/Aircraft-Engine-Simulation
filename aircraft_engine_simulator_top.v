
//* aircraft_engine_simulator_top.v

`timescale 1ns / 1ps

//* ======= Aircraft Engine Simulator Top Module =======
module aircraft_engine_simulator_top #(
    // ------- Parameters. -------
    // Frequencies.
    parameter SYSTEM_CLK_FREQ = 100_000_000, // [Hz].
    parameter TARGET_CLK_FREQ = 1_000,
    
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
    parameter signed [31:0] MASS_OVERFLOW_COOLING_GAIN = 0,

    // Time Constants (Inertia).
    parameter signed [31:0] PRE_CALCULATED_ROTOR_INTERTIAL_TIME_CONST = 0,
    parameter signed [31:0] PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST = 0,
    parameter signed [31:0] PRE_CALCULATED_THERMAL_TIME_CONST = 0,

    // Engine Limits.
    parameter signed [31:0] MAX_ROTATIONAL_SPEED = 0,
    parameter signed [31:0] MAX_COMPRESSOR_TEMPERATURE = 0
)(
    // ------- Inputs. -------
    // System Signals.
    input wire clk, rst,

    // Bus Signals.
    input wire [31:0] bus_addr,
    input wire [31:0] bus_wdata,
    input wire bus_write_en,
    input wire bus_read_en,

    // ------- Outputs. -------
    // Currents.
    output wire signed [31:0] current_fuel_flow,
    output wire signed [31:0] current_speed, current_pressure, current_temperature,

    // Bus Signals.
    output wire [31:0] bus_rdata,

    // Engine Controls.
    output wire fault_compressor_stall,
    output wire fault_sensor_corruption,

    // Flags.
    output wire is_engine_broken
);
    // ------- Local Parameters. -------
    // Data Representation.
    localparam TOTAL_BIT_WIDTH = INTEGER_BIT_WIDTH + FRACTIONAL_BIT_WIDTH;

    // States.
    localparam TOTAL_STATE_COUNT = 4;
    localparam STATE_IDLE = 0;
    localparam STATE_RUNNING = 1;
    localparam STATE_EMERGENCY = 2;
    localparam STATE_SHUTDOWN = 3;

    // ------- Registers. ------
    // Currents.
    reg signed [TOTAL_BIT_WIDTH-1:0] current_fuel_flow_r;
    reg signed [TOTAL_BIT_WIDTH-1:0] current_speed_r;
    reg signed [TOTAL_BIT_WIDTH-1:0] current_pressure_r;
    reg signed [TOTAL_BIT_WIDTH-1:0] current_temperature_r;

    // Flags.
    reg is_engine_broken_r;

    // States.
    reg [$clog2(TOTAL_STATE_COUNT+1)-1:0] current_state;
    reg [$clog2(TOTAL_STATE_COUNT+1)-1:0] next_state;

    // Gains.
    reg signed [TOTAL_BIT_WIDTH-1:0] speed_gain_coeff_r;
    reg signed [TOTAL_BIT_WIDTH-1:0] compressor_pressure_gain_r;
    reg signed [TOTAL_BIT_WIDTH-1:0] combustion_heat_gain_r;
    reg signed [TOTAL_BIT_WIDTH-1:0] mass_overflow_cooling_gain_r;

    // ------- Wires. -------
    // CP.
    wire clk_en_1ms;

    // RI.
    wire start_engine;
    wire restart_engine;
    wire signed [TOTAL_BIT_WIDTH-1:0] fuel_flow_command;

    // TC.
    wire signed [TOTAL_BIT_WIDTH-1:0] target_speed;
    wire signed [TOTAL_BIT_WIDTH-1:0] target_pressure;
    wire signed [TOTAL_BIT_WIDTH-1:0] target_temperature;

    // DC.
    wire signed [TOTAL_BIT_WIDTH-1:0] d_speed;
    wire signed [TOTAL_BIT_WIDTH-1:0] d_pressure;
    wire signed [TOTAL_BIT_WIDTH-1:0] d_temperature;

    // NSC.
    wire signed [TOTAL_BIT_WIDTH-1:0] next_speed; 
    wire signed [TOTAL_BIT_WIDTH-1:0] next_pressure;
    wire signed [TOTAL_BIT_WIDTH-1:0] next_temperature;

    // ------- Assignments. -------
    assign current_fuel_flow = current_fuel_flow_r;
    assign current_speed = current_speed_r;
    assign current_pressure = current_pressure_r;
    assign current_temperature = current_temperature_r;
    assign is_engine_broken = is_engine_broken_r;

    // ------- Modules. -------
    // Clock Prescaler (CP).
    clock_prescaler #(
        // Parameters.
        .SYSTEM_CLK_FREQ(SYSTEM_CLK_FREQ),
        .TARGET_CLK_FREQ(TARGET_CLK_FREQ)
    ) inst_clock_prescaler (
        // Inputs.
        .clk(clk), .rst(rst),

        // Output.
        .clk_en_1ms(clk_en_1ms)
    );

    // Register Interface (RI).
    register_interface #(
        // Parameters.
        .TOTAL_BIT_WIDTH(TOTAL_BIT_WIDTH)
    ) inst_register_interface (
        // Inputs.
        .clk(clk), .rst(rst),

        // Bus Signals.
        .bus_addr(bus_addr),
        .bus_wdata(bus_wdata),
        .bus_write_en(bus_write_en),
        .bus_read_en(bus_read_en),

        // Dependents.
        .current_speed(current_speed_r),
        .current_pressure(current_pressure_r),
        .current_temperature(current_temperature_r),
        .is_engine_broken(is_engine_broken_r),

        // Outputs.
        // Bus Signals.
        .bus_rdata(bus_rdata),

        // Engine Controls.
        .start_engine(start_engine),
        .restart_engine(restart_engine),

        .fuel_flow_command(fuel_flow_command),

        .fault_compressor_stall(fault_compressor_stall),
        .fault_sensor_corruption(fault_sensor_corruption)
    );

    // Target Calculations (TC).
    calculate_target_values #(
        // Parameters.
        // Data Representation.
        .INTEGER_BIT_WIDTH(INTEGER_BIT_WIDTH),
        .FRACTIONAL_BIT_WIDTH(FRACTIONAL_BIT_WIDTH),

        // Ambient Conditions.
        .AMBIENT_PRESSURE(AMBIENT_PRESSURE),
        .AMBIENT_TEMPERATURE(AMBIENT_TEMPERATURE)
    ) inst_calculate_target_values (
        // Inputs.
        .clk(clk), .rst(rst),

        // Dependents.
        .current_fuel_flow(current_fuel_flow_r), 
        .current_rotational_speed(current_speed_r),

        // Gains.
        .speed_gain_coeff(speed_gain_coeff_r),
        .compressor_pressure_gain(compressor_pressure_gain_r),
        .combustion_heat_gain(combustion_heat_gain_r),
        .mass_overflow_cooling_gain(mass_overflow_cooling_gain_r),

        // Outputs.
        // Target States.
        .target_rotational_speed(target_speed), 
        .target_compressor_pressure(target_pressure), 
        .target_exhaust_gas_temperature(target_temperature)
    );

    // Derivative Calculation (DC).
    calculate_derivatives #(
        // Parameters.
        // Data Representation.
        .INTEGER_BIT_WIDTH(INTEGER_BIT_WIDTH),
        .FRACTIONAL_BIT_WIDTH(FRACTIONAL_BIT_WIDTH),

        // Time Constants (Inertia).
        .PRE_CALCULATED_ROTOR_INTERTIAL_TIME_CONST(PRE_CALCULATED_ROTOR_INTERTIAL_TIME_CONST),
        .PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST(PRE_CALCULATED_PRESSURE_VOLUME_TIME_CONST),
        .PRE_CALCULATED_THERMAL_TIME_CONST(PRE_CALCULATED_THERMAL_TIME_CONST)
    ) inst_calculate_derivatives (
        // Inputs.
        .clk(clk), .rst(rst),

        // Currents.
        .current_rotational_speed(current_speed_r), 
        .current_compressor_pressure(current_pressure_r), 
        .current_exhaust_gas_temperature(current_temperature_r),

        // Targets.
        .target_rotational_speed(target_speed), 
        .target_compressor_pressure(target_pressure), 
        .target_exhaust_gas_temperature(target_temperature),

        // Outputs.
        .d_rotational_speed(d_speed), 
        .d_compressor_pressure(d_pressure), 
        .d_exhaust_gas_temperature(d_temperature)
    );

    // Next Step Calculation (NSC).
    // Derivative Calculation (DC).
    calculate_next_steps #(
        // Parameters.
        // Data Representation.
        .INTEGER_BIT_WIDTH(INTEGER_BIT_WIDTH),
        .FRACTIONAL_BIT_WIDTH(FRACTIONAL_BIT_WIDTH),

        // Ambient Conditions.
        .AMBIENT_PRESSURE(AMBIENT_PRESSURE),
        .AMBIENT_TEMPERATURE(AMBIENT_TEMPERATURE)
    ) inst_calculate_next_steps (
        // Inputs.
        // Currents.
        .current_rotational_speed(current_speed_r), 
        .current_compressor_pressure(current_pressure_r), 
        .current_exhaust_gas_temperature(current_temperature_r),

        // Derivatives.
        .d_rotational_speed(d_speed), 
        .d_compressor_pressure(d_pressure), 
        .d_exhaust_gas_temperature(d_temperature),

        // Outputs.
        .next_rotational_speed(next_speed), 
        .next_compressor_pressure(next_pressure), 
        .next_exhaust_gas_temperature(next_temperature)
    );

    // ------- Sequential Logic. -------
    always @(posedge clk) begin
        if (rst) begin
            current_state <= STATE_IDLE;

            // Currents.
            current_fuel_flow_r <= 0;
            current_speed_r <= 0;
            current_pressure_r <= AMBIENT_PRESSURE;
            current_temperature_r <= AMBIENT_TEMPERATURE;

            // Flags.
            is_engine_broken_r <= 0;

            // Gains.
            speed_gain_coeff_r <= 0;
            compressor_pressure_gain_r <= 0;
            combustion_heat_gain_r <= 0;
            mass_overflow_cooling_gain_r <= 0;
        end
        else if (clk_en_1ms) begin
            // Updates the currents to nexts.
            current_state <= next_state;

            current_speed_r <= next_speed;
            current_pressure_r <= next_pressure;
            current_temperature_r <= next_temperature;

            // Flags once a violation occurs so that the system remains tripped.
            case (current_state)
                STATE_IDLE: begin
                    current_fuel_flow_r <= 0;
                    is_engine_broken_r <= 0;
                end

                STATE_RUNNING: begin
                    // Passes normal operational fuel flow and actual gain coefficients.
                    current_fuel_flow_r <= fuel_flow_command;

                    speed_gain_coeff_r <= SPEED_GAIN_COEFF;
                    compressor_pressure_gain_r <= COMPRESSOR_PRESSURE_GAIN;
                    combustion_heat_gain_r <= COMBUSTION_HEAT_GAIN;
                    mass_overflow_cooling_gain_r <= fault_compressor_stall ? 0 : MASS_OVERFLOW_COOLING_GAIN;

                    if ((current_speed_r > MAX_ROTATIONAL_SPEED) || (current_temperature_r > MAX_COMPRESSOR_TEMPERATURE)) is_engine_broken_r <= 1;
                end

                STATE_EMERGENCY: begin
                    // Forces fuel flow to zero and disables the gains to simulate an automatic emergency cut-off.
                    current_fuel_flow_r <= 0;

                    speed_gain_coeff_r <= 0;
                    compressor_pressure_gain_r <= 0;
                    combustion_heat_gain_r <= 0;
                    mass_overflow_cooling_gain_r <= 0;
                end

                STATE_SHUTDOWN: begin
                    current_fuel_flow_r <= 0;
                end
            endcase
        end
    end

    // ------- Combinational Logic. -------
    always @(*) begin
        next_state = current_state;

        case (current_state)
            STATE_IDLE: begin
                if (start_engine) next_state = STATE_RUNNING;
            end

            STATE_RUNNING: begin
                // Passes normal operational fuel flow and actual gain coefficients.
                if ((current_speed_r > MAX_ROTATIONAL_SPEED) || (current_temperature_r > MAX_COMPRESSOR_TEMPERATURE)) next_state = STATE_EMERGENCY;
            end

            STATE_EMERGENCY: begin
                //TODO Add a condition here.
                next_state = STATE_SHUTDOWN;
            end

            STATE_SHUTDOWN: begin
                if (restart_engine) next_state = STATE_IDLE;
            end
        endcase
    end

endmodule
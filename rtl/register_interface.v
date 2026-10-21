
//* register_interface.v

`timescale 1ns / 1ps

//* ======= Register Interface for the Aircraft Engine =======
module register_interface #(
    parameter TOTAL_BIT_WIDTH = 32
)(
    // ------- Inputs. -------
    // System Signals.
    input wire clk, rst,

    // Register Interface.
    input wire [31:0] bus_addr, // Memory address offset (0x00, 0x04, etc.).
    input wire [31:0] bus_wdata, // Data being written by the testbench.
    input wire bus_write_en, // Software wants to write.
    input wire bus_read_en, // Software wants to read.

    // Read-Only Data.
    input wire signed [31:0] current_speed,
    input wire signed [31:0] current_pressure,
    input wire signed [31:0] current_temperature,
    input wire is_engine_broken,

    // ------- Outputs. -------
    // Bus Interface.
    output reg [31:0] bus_rdata, // Data sent back to testbench.

    // Engine Controls.
    output wire start_engine,
    output wire restart_engine,

    output wire signed [31:0] fuel_flow_command,

    output wire fault_compressor_stall,
    output wire fault_sensor_corruption
);
    // ------- Local Parameters. -------
    // Address Map Offsets.
    localparam [7:0] ADDR_CONTROL = 8'h00; // Control Register (Start / Restart).
    localparam [7:0] ADDR_STATUS = 8'h04; // Status Register (Engine Broken Flag).
    localparam [7:0] ADDR_FUEL_FLOW_COMMAND = 8'h08; // Fuel Flow Command.
    localparam [7:0] ADDR_SPEED = 8'h0C; // Rotational Speed.
    localparam [7:0] ADDR_PRESSURE = 8'h10; // Compressor Pressure.
    localparam [7:0] ADDR_TEMPERATURE = 8'h14; // Exhaust Gas Temperature.
    localparam [7:0] ADDR_FAULT_INJECTION = 8'h18; // Intentional Internal Parameter Altercation.

    // Constant.
    localparam ZERO_32BIT = {TOTAL_BIT_WIDTH{1'b0}};

    // ------- Registers. -------
    reg [TOTAL_BIT_WIDTH-1:0] control_reg;
    reg [TOTAL_BIT_WIDTH-1:0] fuel_flow_command_reg;
    reg [TOTAL_BIT_WIDTH-1:0] fault_injection_reg;

    // ------- Assignments. -------
    // Control Bit Mapping.
    assign start_engine = control_reg[0]; // Starts the engine.
    assign restart_engine = control_reg[1]; // Restarts the engine.

    assign fuel_flow_command = fuel_flow_command_reg;

    assign fault_compressor_stall = fault_injection_reg[0]; // Compressor stall disrupts the airflow.
    assign fault_sensor_corruption = fault_injection_reg[1]; // Garbage data tests the detection of a sensor failure.

    // ------- Bus Write Logic. -------
    always @(posedge clk) begin
        if (rst) begin
            control_reg <= ZERO_32BIT;
            fuel_flow_command_reg <= ZERO_32BIT;
            fault_injection_reg <= ZERO_32BIT;
        end
        else begin
            if (bus_write_en) begin
                case (bus_addr[7:0])
                    ADDR_CONTROL: control_reg <= bus_wdata;

                    ADDR_FUEL_FLOW_COMMAND: fuel_flow_command_reg <= bus_wdata;

                    ADDR_FAULT_INJECTION: fault_injection_reg <= bus_wdata;

                    //? 'default: ;': Acts as a null statement (does nothing).
                    default: ;// Read-only or unmapped addresses are ignored.
                endcase
            end
        end
    end

    // ------- Bus Read Logic. -------
    always @(posedge clk) begin
        if (rst) bus_rdata <= ZERO_32BIT;

        else if (bus_read_en) begin
            case (bus_addr[7:0])
                ADDR_CONTROL: bus_rdata <= control_reg;

                // Packs the 1-bit boolean status into 32-bit word.
                ADDR_STATUS: bus_rdata <= { {(TOTAL_BIT_WIDTH-1){1'b0}}, is_engine_broken };

                ADDR_FUEL_FLOW_COMMAND: bus_rdata <= fuel_flow_command_reg;

                ADDR_SPEED: bus_rdata <= current_speed;

                ADDR_PRESSURE: bus_rdata <= current_pressure;

                ADDR_TEMPERATURE: bus_rdata <= current_temperature;

                ADDR_FAULT_INJECTION: bus_rdata <= fault_injection_reg;

                //? '32'hDEAD_BEEF': Debug number.
                // Returns when an address tries to get read, that doesn't exist.
                default: bus_rdata <= 32'hDEAD_BEEF;
            endcase
        end

        else bus_rdata <= ZERO_32BIT;
    end
endmodule
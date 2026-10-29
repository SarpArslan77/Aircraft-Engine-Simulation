//* axi4_lite.v

//* The 'VALID' / 'READY' Handshake:
// Every AXI channel transfers data using a two-way handshake. A transfer
//      occurs on the rising clock edge only when both (VALID == 1) and (READY == 1).
// The master drives 'VALID' high when data/address is ready.
// The slave drives 'READY' high when it can accept it.

`timescale 1ns / 1ps

//* ======= Register Interface for the Aircraft Engine =======
module axi4_lite #(
    // ------- Parameter. -------
    parameter TOTAL_BIT_WIDTH = 32
)(
    // ------- Inputs. -------
    // System Signals.
    input wire s_axi_aclk, s_axi_aresetn,

    // AXI4-Lite Slave Channels.
    // -> Write Address (AW): Tells the slave where the master wants to write.
    //? s_axi_awaddr: Target memory address, where the write operation should take place.
    input wire [TOTAL_BIT_WIDTH-1:0] s_axi_awaddr,
    //? s_axi_awprot: Privlige attribute for the access:
    //      -> Bit 0: Normal (0) vs. Privileged access (1).
    //      -> Bit 1: Secure (0) vs. Non-secure access (1).
    //      -> Bit 2: Data (0) vs. Instruction access (1).
    input wire [2:0] s_axi_awprot,
    //? s_axi_awvalid: Indicates the write address and control signals ('awaddr' and 'awprot') are valid.
    input wire s_axi_awvalid,

    // -> Write Data (W): Delivers the actual data to be written.
    //? s_axi_wdata: Data to be written into the memory.
    input wire [TOTAL_BIT_WIDTH-1:0] s_axi_wdata,
    //? s_axi_wstrb: Byte-enable qualifiers:
    //      -> wstrb[0] = 1: Write byte 0 (wdata[7:0]).
    //      -> wstrb[1] = 1: Write byte 1 (wdata[15:8]).
    
    //      -> wstrb[2] = 1: Write byte 2 (wdata[23:16]).
    //      -> wstrb[3] = 1: Write byte 3 (wdata[31:24]).
    input wire [3:0] s_axi_wstrb,
    //? s_axi_wvalid: Indicates 'wdata' and 'wstrb' are valid.
    input wire s_axi_wvalid,

    // -> Write Response (B): After a write operation completes, this channel
    //      sends and acknowledgment back to the master.
    //? s_axi_bready:  Indicates master is ready to accept the response.
    input wire s_axi_bready,

    // -> Read Address (AR): Tells slave where the master wants to read from.
    //? s_axi_araddr: Target memory address from which to read data.
    input wire [TOTAL_BIT_WIDTH-1:0] s_axi_araddr,
    //? s_axi_arpot: Read protection attributes (identical definition to 'awprot').
    input wire [2:0] s_axi_arprot,
    //? s_axi_arvalid: Indicates the read address is valid.
    input wire s_axi_arvalid,

    // -> Read Data (R): Sends both the requested data and a status response back to master.
    //? s_axi_rready: Indicates the master is ready to accept the incoming read data.
    input wire s_axi_rready,

    // Engine Telemetrics.
    input wire signed [TOTAL_BIT_WIDTH-1:0] current_speed,
    input wire signed [TOTAL_BIT_WIDTH-1:0] current_pressure,
    input wire signed [TOTAL_BIT_WIDTH-1:0] current_temperature,
    input wire is_engine_broken,

    // ------- Outputs. -------
    // AXI4-Lite Slave Channels.
    // -> AW.
    //? s_axi_awready: Indicates the slave is ready to accept the write address.
    output reg s_axi_awready,

    // -> W.
    //? s_axi_wready: Indicates slave is ready to accept the write data.
    output reg s_axi_wready,

    // -> B.
    //? s_axi_bresp: Status code indicating whether the write succeeded:
    //      -> 2'b00 (OKAY): Normal access success.
    //      -> 2'b01 (EXOKAY): Exclusive access success.
    //      -> 2'b10 (SLVERR): Slave error.
    //      -> 2'b11 (DECERR): Decode error, interconnect could not find target.
    output reg [1:0] s_axi_bresp,
    //? s_axi_bvalid: Indicates the write response 'bresp' is valid.
    output reg s_axi_bvalid,

    // -> AR.
    //? s_axi_arready: Indicates the slave is ready to accept read address.
    output reg s_axi_arready,

    // - R.
    //? s_axi_rvalid: Indicates the read data 'rdata' and status 'rresp' are valid.
    output reg s_axi_rvalid,
    //? s_axi_rdata: Actual data retrieved from the memory location requested by 'araddr'.
    output reg signed [TOTAL_BIT_WIDTH-1:0] s_axi_rdata,
    //? s_axi_rresp: Status code indicating whether the read was successful (identical definition to 'bresp').
    output reg [1:0] s_axi_rresp,

    // Engine Controls.
    output wire start_engine,
    output wire restart_engine,

    output wire signed [TOTAL_BIT_WIDTH-1:0] fuel_flow_command,

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
    localparam [TOTAL_BIT_WIDTH-1:0] ZERO_32BIT = {TOTAL_BIT_WIDTH{1'b0}};

    // ------- Registers. -------
    reg [TOTAL_BIT_WIDTH-1:0] control_reg;
    reg [TOTAL_BIT_WIDTH-1:0] fuel_flow_command_reg;
    reg [TOTAL_BIT_WIDTH-1:0] fault_injection_reg;

    // ------- Assignments. -------
    assign start_engine = control_reg[0]; // Starts the engine.
    assign restart_engine = control_reg[1]; // Restarts the engine.

    assign fuel_flow_command = fuel_flow_command_reg;

    assign fault_compressor_stall = fault_injection_reg[0]; // Compressor stall disrupts the airflow.
    assign fault_sensor_corruption = fault_injection_reg[1]; // Garbage data tests the detection of a sensor failure.

    // ------- Integers. -------
    integer i;

    // ------- Write Path. -------
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            s_axi_awready <= 0;
            s_axi_wready <= 0;
            s_axi_bvalid <= 0;

            s_axi_bresp <= 2'b00;

            control_reg <= 0;
            fuel_flow_command_reg <= 0;
            fault_injection_reg <= 0;
        end
        else begin
            // Idle: Slave is ready to accept data from master.
            if (!s_axi_bvalid) begin
                if (s_axi_awvalid && s_axi_wvalid) begin
                    s_axi_awready <= 1;
                    s_axi_wready <= 1;

                    // Assumes slave's writing operation is successfull (if not, will be overwritten in case statements).
                    s_axi_bresp <= 2'b00;

                    case (s_axi_awaddr[7:0])
                        ADDR_CONTROL: begin
                            for(i = 0; i < 4; i = i + 1) begin
                                if (s_axi_wstrb[i]) control_reg[(i*8) +: 8] <= s_axi_wdata[(i*8) +: 8];
                            end
                        end

                        ADDR_FUEL_FLOW_COMMAND: begin
                            for(i = 0; i < 4; i = i + 1) begin
                                if (s_axi_wstrb[i]) fuel_flow_command_reg[(i*8) +: 8] <= s_axi_wdata[(i*8) +: 8];
                            end
                        end

                        ADDR_FAULT_INJECTION: begin
                            for(i = 0; i < 4; i = i + 1) begin
                               if (s_axi_wstrb[i]) fault_injection_reg[(i*8) +: 8] <= s_axi_wdata[(i*8) +: 8];
                            end
                        end

                        // Read-only or unmapped addresses.
                        default: s_axi_bresp <= 2'b10;
                    endcase

                    s_axi_bvalid <= 1;
                end
                else begin
                    s_axi_awready <= 0;
                    s_axi_wready <= 0;
                end
            end
            // Slave is waiting for a response from master.
            else begin
                s_axi_awready <= 0;
                s_axi_wready <= 0;

                // If master acknowledges recept, signals transaction completion.
                if (s_axi_bready) s_axi_bvalid <= 0;
            end
        end
    end

    // ------- Read Path. -------
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            s_axi_arready <= 0;
            s_axi_rvalid <= 0;

            s_axi_rdata <= 0;
        end
        else begin
            // Slave is currently not holding unread data for the master.
            if (!s_axi_rvalid) begin
                // Checks if the master is requesting a read 's_axi_arvalid'.
                if (s_axi_arvalid) begin
                    // Accepts the read address.
                    s_axi_arready <= 1;
                    s_axi_rresp <= 2'b00;

                    case (s_axi_araddr[7:0])
                        ADDR_CONTROL: s_axi_rdata <= control_reg;

                        ADDR_STATUS: s_axi_rdata <= { { (TOTAL_BIT_WIDTH-1){1'b0} }, is_engine_broken };

                        ADDR_FUEL_FLOW_COMMAND: s_axi_rdata <= fuel_flow_command_reg;

                        ADDR_SPEED: s_axi_rdata <= fault_sensor_corruption ? 32'hDEAD_BEEF : current_speed;

                        ADDR_PRESSURE: s_axi_rdata <= fault_sensor_corruption ? 32'hDEAD_BEEF : current_pressure;

                        ADDR_TEMPERATURE: s_axi_rdata <= fault_sensor_corruption ? 32'hDEAD_BEEF : current_temperature;

                        ADDR_FAULT_INJECTION: s_axi_rdata <= fault_injection_reg;

                        default: begin
                            s_axi_rresp <= 2'b10;
                            s_axi_rdata <= 32'hDEAD_BEEF;
                        end
                    endcase

                    // Data is presented to the master on the next cycle.
                    s_axi_rvalid <= 1;
                end
                else begin
                    s_axi_arready <= 0;
                end
            end
            // Holds data for the master.
            else begin
                // Slave is busy returning data.
                s_axi_arready <= 0;

                // Checks if the master acknowledges receipt, if yes, signals the transaction is complete.
                if (s_axi_rready) s_axi_rvalid <= 0;
            end
        end
    end
endmodule

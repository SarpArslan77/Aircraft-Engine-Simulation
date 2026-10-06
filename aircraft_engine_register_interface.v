
//* aircraft_engine_register_interface.v

`timescale 1ns / 1ps

//* ======= Register Interface for the Aircraft Engine =======
module aircraft_engine_register_interface #(

)(
    // ------- Inputs. -------
    // System Signals.
    input wire clk, rst,

    // Register Interface.
    input wire [31:0] buss_addr, // Memory address offset (0x00, 0x04, etc.).
    input wire [31:0] bus_wdata, // Data being written by the testbench.
    input wire bus_write_en, // Software wants to write.
    input wire bus_read_en, // Software wants to read.
    
);

endmodule
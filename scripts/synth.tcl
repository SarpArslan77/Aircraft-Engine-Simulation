
#* scripts/synth.tcl

#* ======= Vivado Automated Out-of-Context (OOC) Synthesis & Timing Run =======

#? Tcl: Tool Command Language.
# -> 'Everything is a Command': In Tcl, every line starts with a command
#       followed by arguments seperated by spaces: command arg1 arg2.
# -> Creating Variables 'set' and Reading Variables '$'
# -> Square Brackets '[]' Mean 'Run This Sub-Command First'
# -> Double Quotes ' " ' vs. Curly Braces '{}':
#       - Double Quotes ' "..." ': Allow variables '$' and commands '[]' 
#           to be evaluated inside.
#       - Curly Braces '{}': Completely raw literal text, blocks any evaluation.

# Automatically determines the project root directory.
set SCRIPTS_DIR [file dirname [file normalize [info script]]]
set MAIN_DIR [file normalize "$SCRIPTS_DIR/.."]

# Sets the target device (f.e. AMD/Xilinx Artix-7).
set PART "xc7a35tcpg236-1"

set TOP_MODULE "aircraft_engine_simulator_top"
set OUTPUT_DIR "$MAIN_DIR/build_synth"

#? file mkdir: Creates a folder.
# Creates a output directory.
file mkdir $OUTPUT_DIR

#? read_verilog: Parses data into its in-memory database.
# Adds all the RTL source files.
read_verilog [glob "$MAIN_DIR/rtl/*.v"]

#? synth_design: Core synthesis engine.
#? -top: Tells Vivado which module is the master root.
#? -part: Tells Vivado which specific FPGA silicon to map the gates onto.
#? -mode out_of_context: Tells Vivado: "Do not attach physical package pins".
# Synthesizes in Out-of-Context mode.
synth_design -top $TOP_MODULE -part $PART -mode out_of_context

# Reads the target period from command-line arguments (defaults to 10.0).
if { $argc > 0 } {
    set PERIOD [lindex $argv 0]
} else {
    set PERIOD 10.000
}

#? [get_ports clk]: Queries Vivado's databse to find the physical input wire.
#? create_clock -period: Defines an SDC / XDC timing constraint.
# Applies a 100 MHz virtual clock constraint.
create_clock -period $PERIOD -name sys_clk [get_ports s_axi_aclk]

#? opt_design: Logic optimization.
#? place_design: Physical placement.
#? route_design: Physical routing.
# Runs physical implementation.
opt_design
place_design
route_design

#? report_utilization: Generates a listing of LUT, FF, DSP Slices.
#? report_timing_summary: Performs Static Timing Analysis (STA) and
#       calculates the Worst Negative Slack (WNS).
#? -file: Saves the files to specified path.
# Exports reports.
report_utilization -file "$OUTPUT_DIR/utilization.rpt"
report_timing_summary -file "$OUTPUT_DIR/timing.rpt"

#? puts: Prints.
#? exit: Closes Vivado.
puts "Synthesis and Implementation complete! Reports saved to $OUTPUT_DIR"
exit
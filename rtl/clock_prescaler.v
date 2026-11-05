
//* rtl/clock_prescaler.v

`timescale 1ns / 1ps

//* ======= Clock Prescaler =======
module clock_prescaler #(
    // ------- Parameters. -------
    parameter SYSTEM_CLK_FREQ = 100_000_000, // [Hz].
    parameter TARGET_CLK_FREQ = 1_000
)(
    // ------- Inputs. -------
    input wire clk, rst,

    // ------- Output. -------
    output reg clk_en_1ms
);
    // ------- Local Parameter. -------
    localparam [31:0] COUNTER_LIMIT = SYSTEM_CLK_FREQ / TARGET_CLK_FREQ;
    localparam COUNTER_WIDTH = $clog2(COUNTER_LIMIT + 1);
    localparam [COUNTER_WIDTH-1:0] COUNTER_MAX = COUNTER_LIMIT[COUNTER_WIDTH-1:0] - 1'b1;

    // ------- Register. -------
    reg [COUNTER_WIDTH-1:0] counter;

    // ------- Sequential Logic. -------
    always @(posedge clk) begin
        if (rst) begin
            counter <= 0;

            clk_en_1ms <= 0;
        end
        else begin
            if (counter == COUNTER_MAX) begin
                counter <= 0;

                clk_en_1ms <= 1;
            end
            else begin
                counter <= counter + 1;

                clk_en_1ms <= 0;
            end
        end
    end
endmodule

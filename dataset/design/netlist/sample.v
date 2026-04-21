// dataset/design/netlist/sample.v
module sample_top (input wire a, b, c, output wire out0, out1);
    wire n1, n2, n3;
    and  U1 (n1, a, b);
    not  U2 (n2, c);
    or   U3 (n3, n1, n2);
    buf  U4 (out0, n3);
    xor  U5 (out1, a, c);
endmodule

from __future__ import annotations

from typing import Iterable, List

from .netlist import Gate, Netlist


def write_verilog(netlist: Netlist, path: str) -> None:
    inputs = sorted(netlist.inputs)
    outputs = sorted(netlist.outputs)
    wires = sorted(netlist.wires - netlist.inputs - netlist.outputs)

    lines: List[str] = []
    port_list = ", ".join([*inputs, *outputs])
    lines.append(f"module {netlist.name} ({port_list});")

    if inputs:
        lines.append(f"    input {', '.join(inputs)};")
    if outputs:
        lines.append(f"    output {', '.join(outputs)};")
    if wires:
        lines.append(f"    wire {', '.join(wires)};")

    for gate in netlist.gates:
        ports = ", ".join([gate.output, *gate.inputs])
        lines.append(f"    {gate.type} {gate.name} ({ports});")

    lines.append("endmodule")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

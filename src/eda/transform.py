from __future__ import annotations

from typing import List, Optional, Set, Tuple

from .analysis import build_net_graph, max_depth, cone
from .netlist import Gate, Netlist


def insert_gate(netlist: Netlist, gate_type: str, pattern: str, extra_input: str) -> Gate:
    base_name = f"ins_{gate_type}_{len(netlist.gates) + 1}"
    new_output = f"{pattern}_ins_{len(netlist.gates) + 1}"
    new_gate = Gate(name=base_name, type=gate_type.lower(), inputs=[pattern, extra_input], output=new_output)

    _drivers, loads = netlist.build_net_drivers_and_loads()
    for load_gate in loads.get(pattern, []):
        load_gate.inputs = [new_output if n == pattern else n for n in load_gate.inputs]

    netlist.add_gate(new_gate)
    netlist.wires.add(new_output)
    return new_gate


def replace_gate(netlist: Netlist, gate_name: str, new_type: str) -> bool:
    gate = netlist.gate_by_name(gate_name)
    if not gate:
        return False
    gate.type = new_type.lower()
    return True


def remove_dead_logic(netlist: Netlist) -> int:
    _adj, rev = build_net_graph(netlist)
    live_gates: Set[str] = set()
    stack = list(netlist.outputs)
    seen_nets: Set[str] = set()

    while stack:
        net = stack.pop()
        if net in seen_nets:
            continue
        seen_nets.add(net)
        for prev_net, gate in rev.get(net, []):
            live_gates.add(gate.name)
            if prev_net not in seen_nets:
                stack.append(prev_net)

    before = len(netlist.gates)
    netlist.gates = [g for g in netlist.gates if g.name in live_gates]
    return before - len(netlist.gates)


def optimize_cone(netlist: Netlist, output_net: str, max_depth_limit: int) -> str:
    removed = 0
    while True:
        depth, _path = max_depth(netlist, _infer_input(netlist), output_net)
        if depth <= max_depth_limit or depth < 0:
            break
        removed_in_pass = _remove_one_buffer(netlist, output_net)
        if removed_in_pass == 0:
            break
        removed += removed_in_pass

    return f"Removed {removed} buffers in cone of {output_net}."


def _remove_one_buffer(netlist: Netlist, output_net: str) -> int:
    gates = cone(netlist, output_net)
    for gate in gates:
        if gate.type == "buf" and len(gate.inputs) == 1:
            src = gate.inputs[0]
            dst = gate.output
            _drivers, loads = netlist.build_net_drivers_and_loads()
            for load_gate in loads.get(dst, []):
                load_gate.inputs = [src if n == dst else n for n in load_gate.inputs]
            netlist.gates = [g for g in netlist.gates if g.name != gate.name]
            return 1
    return 0


def _infer_input(netlist: Netlist) -> str:
    return next(iter(netlist.inputs)) if netlist.inputs else ""

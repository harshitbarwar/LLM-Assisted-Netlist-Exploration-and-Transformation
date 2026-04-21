from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass
class Gate:
    name: str
    type: str
    inputs: List[str]
    output: str


@dataclass
class Netlist:
    name: str
    inputs: Set[str] = field(default_factory=set)
    outputs: Set[str] = field(default_factory=set)
    wires: Set[str] = field(default_factory=set)
    gates: List[Gate] = field(default_factory=list)

    def all_nets(self) -> Set[str]:
        return set(self.inputs) | set(self.outputs) | set(self.wires)

    def add_gate(self, gate: Gate) -> None:
        self.gates.append(gate)
        self.wires.add(gate.output)
        for net in gate.inputs:
            if net not in self.inputs and net not in self.outputs:
                self.wires.add(net)

    def remove_gate(self, gate_name: str) -> None:
        self.gates = [g for g in self.gates if g.name != gate_name]

    def gate_by_name(self, gate_name: str) -> Optional[Gate]:
        for gate in self.gates:
            if gate.name == gate_name:
                return gate
        return None

    def build_net_drivers_and_loads(
        self,
    ) -> Tuple[Dict[str, Optional[Gate]], Dict[str, List[Gate]]]:
        drivers: Dict[str, Optional[Gate]] = {net: None for net in self.all_nets()}
        loads: Dict[str, List[Gate]] = {net: [] for net in self.all_nets()}

        for gate in self.gates:
            drivers[gate.output] = gate
            for net in gate.inputs:
                if net not in loads:
                    loads[net] = []
                loads[net].append(gate)

        for net in self.inputs:
            drivers[net] = None
        return drivers, loads

    def clone(self) -> "Netlist":
        return Netlist(
            name=self.name,
            inputs=set(self.inputs),
            outputs=set(self.outputs),
            wires=set(self.wires),
            gates=[Gate(g.name, g.type, list(g.inputs), g.output) for g in self.gates],
        )

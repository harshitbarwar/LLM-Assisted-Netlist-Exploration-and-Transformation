from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .netlist import Gate, Netlist


def build_net_graph(netlist: Netlist) -> Tuple[Dict[str, List[Tuple[str, Gate]]], Dict[str, List[Tuple[str, Gate]]]]:
    adj: Dict[str, List[Tuple[str, Gate]]] = {}
    rev: Dict[str, List[Tuple[str, Gate]]] = {}

    for net in netlist.all_nets():
        adj[net] = []
        rev[net] = []

    for gate in netlist.gates:
        for in_net in gate.inputs:
            adj.setdefault(in_net, []).append((gate.output, gate))
            rev.setdefault(gate.output, []).append((in_net, gate))

    return adj, rev


def max_depth(netlist: Netlist, src: str, dst: str) -> Tuple[int, List[str]]:
    adj, _ = build_net_graph(netlist)
    memo: Dict[str, Optional[Tuple[int, List[str]]]] = {}
    visiting: Set[str] = set()

    def dfs(net: str) -> Optional[Tuple[int, List[str]]]:
        if net == dst:
            return 0, [net]
        if net in visiting:
            return None
        if net in memo:
            return memo[net]

        visiting.add(net)
        best: Optional[Tuple[int, List[str]]] = None
        for next_net, gate in adj.get(net, []):
            result = dfs(next_net)
            if result is None:
                continue
            depth, path = result
            candidate_depth = depth + 1
            candidate_path = [net, f"[{gate.type.upper()}] {gate.name}"] + path
            if best is None or candidate_depth > best[0]:
                best = (candidate_depth, candidate_path)

        visiting.remove(net)
        memo[net] = best
        return best

    result = dfs(src)
    if result is None:
        return -1, []
    return result


def path_exists(netlist: Netlist, src: str, dst: str) -> bool:
    adj, _ = build_net_graph(netlist)
    queue = [src]
    seen: Set[str] = set()
    while queue:
        net = queue.pop(0)
        if net == dst:
            return True
        if net in seen:
            continue
        seen.add(net)
        for next_net, _gate in adj.get(net, []):
            if next_net not in seen:
                queue.append(next_net)
    return False


def path_through(netlist: Netlist, src: str, dst: str, through: str) -> bool:
    return path_exists(netlist, src, through) and path_exists(netlist, through, dst)


def cone(netlist: Netlist, output_net: str) -> List[Gate]:
    _adj, rev = build_net_graph(netlist)
    seen_nets: Set[str] = set()
    seen_gates: Set[str] = set()
    stack = [output_net]
    gates: List[Gate] = []

    while stack:
        net = stack.pop()
        if net in seen_nets:
            continue
        seen_nets.add(net)
        for prev_net, gate in rev.get(net, []):
            if gate.name not in seen_gates:
                gates.append(gate)
                seen_gates.add(gate.name)
            if prev_net not in seen_nets:
                stack.append(prev_net)

    return gates

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from pyverilog.vparser.parser import parse
from pyverilog.vparser import ast as vast

from .netlist import Gate, Netlist


def parse_verilog(path: str) -> Netlist:
    try:
        ast, _ = parse([path])
        module_defs = [d for d in ast.description.definitions if isinstance(d, vast.ModuleDef)]
        if not module_defs:
            raise ValueError("No module definition found in Verilog file.")

        module = module_defs[0]
        netlist = Netlist(name=module.name)

        for item in module.items:
            if isinstance(item, vast.Decl):
                for decl in item.list:
                    if isinstance(decl, vast.Input):
                        netlist.inputs.add(decl.name)
                    elif isinstance(decl, vast.Output):
                        netlist.outputs.add(decl.name)
                    elif isinstance(decl, vast.Wire):
                        netlist.wires.add(decl.name)
            elif isinstance(item, vast.InstanceList):
                gate_type = item.module
                for inst in item.instances:
                    gate = _parse_instance(gate_type, inst)
                    netlist.add_gate(gate)

        return netlist
    except Exception:
        return _parse_simple_verilog(path)


def _parse_simple_verilog(path: str) -> Netlist:
    text = _strip_comments(Path(path).read_text(encoding="utf-8", errors="ignore"))

    module_match = re.search(r"\bmodule\s+(\w+)\s*\((.*?)\)\s*;", text, re.DOTALL)
    if not module_match:
        raise ValueError("No module definition found in Verilog file.")

    module_name = module_match.group(1)
    header_ports = module_match.group(2)
    netlist = Netlist(name=module_name)

    header_inputs, header_outputs = _parse_header_ports(header_ports)
    netlist.inputs.update(header_inputs)
    netlist.outputs.update(header_outputs)

    # Remove the module header so input/output parsing below doesn't misread it.
    text = text.replace(module_match.group(0), "")

    for decl_match in re.finditer(r"\b(input|output|wire)\b\s+([^;]+);", text):
        kind = decl_match.group(1)
        names = _split_decl_list(decl_match.group(2))
        if kind == "input":
            netlist.inputs.update(names)
        elif kind == "output":
            netlist.outputs.update(names)
        else:
            netlist.wires.update(names)

    for gate_match in re.finditer(r"\b(and|or|nand|nor|not|buf|xor|xnor)\b\s+(\w+)\s*\(([^\)]+)\)\s*;", text):
        gate_type = gate_match.group(1)
        gate_name = gate_match.group(2)
        ports = [p.strip() for p in gate_match.group(3).split(",") if p.strip()]
        if not ports:
            continue
        output = ports[0]
        inputs = ports[1:]
        netlist.add_gate(Gate(name=gate_name, type=gate_type.lower(), inputs=inputs, output=output))

    return netlist


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//.*", "", text)
    return text


def _split_decl_list(decl: str) -> List[str]:
    decl = re.sub(r"\b(wire|reg|input|output)\b", "", decl)
    decl = re.sub(r"\[[^\]]+\]", "", decl)
    cleaned = []
    for part in decl.split(","):
        name = part.strip().strip(")").strip()
        if name:
            cleaned.append(name)
    return cleaned


def _parse_header_ports(header: str) -> tuple[set[str], set[str]]:
    inputs: set[str] = set()
    outputs: set[str] = set()
    current: str | None = None

    for raw in header.split(","):
        segment = raw.strip()
        if not segment:
            continue

        if re.search(r"\binput\b", segment):
            current = "input"
        if re.search(r"\boutput\b", segment):
            current = "output"

        name = re.sub(r"\b(input|output|wire|reg)\b", "", segment)
        name = re.sub(r"\[[^\]]+\]", "", name).strip().strip(")")
        if not name:
            continue

        if current == "input":
            inputs.add(name)
        elif current == "output":
            outputs.add(name)

    return inputs, outputs


def _parse_instance(gate_type: str, inst: vast.Instance) -> Gate:
    port_nets: List[str] = []
    for port in inst.portlist:
        if isinstance(port, vast.PortArg):
            if isinstance(port.argname, vast.Identifier):
                port_nets.append(port.argname.name)
            elif isinstance(port.argname, vast.IntConst):
                port_nets.append(port.argname.value)
            else:
                port_nets.append(str(port.argname))
        else:
            port_nets.append(str(port))

    if not port_nets:
        raise ValueError(f"Gate instance {inst.name} has no ports.")

    output = port_nets[0]
    inputs = port_nets[1:]
    return Gate(name=inst.name, type=gate_type.lower(), inputs=inputs, output=output)

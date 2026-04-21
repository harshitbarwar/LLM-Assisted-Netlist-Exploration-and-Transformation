from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .agent import get_command
from .eda.analysis import max_depth, path_through
from .eda.parser import parse_verilog
from .eda.transform import insert_gate, optimize_cone, remove_dead_logic, replace_gate
from .eda.writer import write_verilog
from .logger import ResponseLogger


def execute_command(netlist, command: Dict[str, Any]) -> object:
    cmd = command.get("command")
    args = command.get("args", {})

    if cmd == "SET_CASE":
        return {"__set_case__": args.get("name")}

    if cmd == "READ_DESIGN":
        path = args.get("path")
        if not path:
            return "Missing path for READ_DESIGN."
        netlist = parse_verilog(path)
        return f"Loaded {path} successfully.", netlist

    if netlist is None:
        return "No design loaded. Use READ_DESIGN first."

    if cmd == "WRITE_DESIGN":
        path = args.get("path")
        if not path:
            return "Missing path for WRITE_DESIGN."
        write_verilog(netlist, path)
        return f"Wrote design to {path}."

    if cmd == "MAX_DEPTH":
        src = args.get("from")
        dst = args.get("to")
        if not src or not dst:
            return "Missing 'from' or 'to' for MAX_DEPTH."
        depth, path = max_depth(netlist, src, dst)
        if depth < 0:
            return f"No path found from {src} to {dst}."
        return f"Maximum logic depth from {src} to {dst} is {depth}.\nPath: " + " -> ".join(path)

    if cmd == "PATH_QUERY":
        src = args.get("from")
        dst = args.get("to")
        through = args.get("through")
        if not src or not dst or not through:
            return "Missing 'from', 'to', or 'through' for PATH_QUERY."
        answer = path_through(netlist, src, dst, through)
        return "Yes" if answer else "No"

    if cmd == "INSERT_GATE":
        gate_type = args.get("type")
        pattern = args.get("pattern")
        extra_input = args.get("extra_input")
        if not gate_type or not pattern or not extra_input:
            return "Missing 'type', 'pattern', or 'extra_input' for INSERT_GATE."
        gate = insert_gate(netlist, gate_type, pattern, extra_input)
        return f"Inserted {gate.type} gate {gate.name} on {pattern}."

    if cmd == "REPLACE_GATE":
        pattern = args.get("pattern")
        new_type = args.get("new_type")
        if not pattern or not new_type:
            return "Missing 'pattern' or 'new_type' for REPLACE_GATE."
        ok = replace_gate(netlist, pattern, new_type)
        return f"Replaced gate {pattern} with {new_type}." if ok else f"Gate {pattern} not found."

    if cmd == "REMOVE_DEAD":
        removed = remove_dead_logic(netlist)
        return f"Removed {removed} dead gates."

    if cmd == "OPTIMIZE_CONE":
        output_net = args.get("output")
        max_depth_limit = args.get("max_depth")
        if not output_net or max_depth_limit is None:
            return "Missing 'output' or 'max_depth' for OPTIMIZE_CONE."
        return optimize_cone(netlist, output_net, int(max_depth_limit))

    return "Unknown command."


class BackendSession:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.netlist = None
        self.case_name: Optional[str] = None
        self.response_id = 1
        self.logger = ResponseLogger(self.case_name)

    def reset(self) -> None:
        self.netlist = None
        self.case_name = None
        self.response_id = 1
        self.logger = ResponseLogger(self.case_name)

    def process_query(self, request: str) -> Dict[str, Any]:
        command = get_command(request, self.config)
        result = execute_command(self.netlist, command)

        if isinstance(result, tuple):
            message, self.netlist = result
        elif isinstance(result, dict) and "__set_case__" in result:
            self.case_name = result["__set_case__"]
            self.logger = ResponseLogger(self.case_name)
            message = (
                f"Acknowledged. Testcase \"{self.case_name}\" initialized. "
                f"Logging to {self.case_name}.log."
            )
        else:
            message = result

        block = f"#RESPONSE {self.response_id}\n{message}\n#END {self.response_id}"
        self.logger.log(block)

        response_id = self.response_id
        self.response_id += 1

        return {
            "message": message,
            "block": block,
            "response_id": response_id,
            "command": command,
            "case_name": self.case_name,
        }

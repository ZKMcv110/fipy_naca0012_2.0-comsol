#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Mini COMSOL MCP demo similar to the project's heat-exchanger workflow.

Default mode is dry-run: it prints the MCP tool calls without starting COMSOL.
Use --check-mcp to verify that the MCP server responds.
Use --execute with either --start-comsol or --connect-port to actually call
COMSOL-backed modeling tools.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


MCP_ROOT = Path(r"C:\Users\20614\mcp_servers\COMSOL_Multiphysics_MCP")
MCP_PYTHON = MCP_ROOT / ".venv" / "Scripts" / "python.exe"
OUT_DIR = Path(__file__).parent / "demo_outputs"


@dataclass(frozen=True)
class DemoParameters:
    channel_length: str = "30[mm]"
    channel_height: str = "9[mm]"
    tube_radius: str = "0.45[mm]"
    streamwise_pitch: str = "4.0[mm]"
    transverse_pitch: str = "2.0[mm]"
    stagger_offset: str = "1.2[mm]"
    inlet_velocity: str = "5[m/s]"
    inlet_temperature: str = "293.15[K]"
    wall_temperature: str = "373.15[K]"


DEMO_PARAMETERS = DemoParameters()


def server_params() -> StdioServerParameters:
    from mcp import StdioServerParameters

    return StdioServerParameters(
        command=str(MCP_PYTHON),
        args=["-m", "src.server"],
        env={
            "PYTHONPATH": str(MCP_ROOT),
            "HF_ENDPOINT": "https://hf-mirror.com",
        },
    )


def demo_tool_plan() -> list[dict[str, Any]]:
    """Return a representative tool-call sequence for the MCP demo."""
    p = DEMO_PARAMETERS
    calls: list[dict[str, Any]] = []

    calls.append({"tool": "model_create", "args": {"name": "mcp_demo_staggered_tube_channel", "set_current": True}})
    calls.append({"tool": "model_create_component", "args": {"component_name": "comp1"}})
    calls.append({"tool": "geometry_create", "args": {"geometry_name": "geom1", "space_dimension": 2, "component_name": "comp1"}})

    for name, value in asdict(p).items():
        calls.append({"tool": "param_set", "args": {"name": name, "value": value, "description": "MCP demo parameter"}})

    calls.append({
        "tool": "geometry_add_rectangle",
        "args": {
            "feature_name": "channel",
            "geometry_name": "geom1",
            "position": [0.0, -0.0045],
            "size": [0.030, 0.009],
        },
    })

    # Six staggered heated cylinders, simplified from your multi-row tube/airfoil idea.
    tube_centers = [
        (0.006, -0.002), (0.010, 0.000), (0.014, -0.002),
        (0.006, 0.002), (0.010, 0.004), (0.014, 0.002),
    ]
    for i, (x, y) in enumerate(tube_centers, start=1):
        calls.append({
            "tool": "geometry_add_circle",
            "args": {
                "geometry_name": "geom1",
                "position": [x, y],
                "radius": 0.00045,
            },
            "note": f"heated tube {i}",
        })

    calls.extend([
        {"tool": "geometry_build", "args": {"geometry_name": "geom1", "component_name": "comp1"}},
        {"tool": "geometry_get_boundaries", "args": {"geometry_name": "geom1"}},
        {"tool": "physics_add_laminar_flow", "args": {}},
        {"tool": "physics_add_heat_transfer", "args": {}},
        {
            "tool": "physics_interactive_setup_flow",
            "args": {"physics_name": "Laminar Flow"},
            "note": "Use returned boundary numbers before setting inlet/outlet.",
        },
        {
            "tool": "physics_interactive_setup_heat",
            "args": {"physics_name": "Heat Transfer in Solids"},
            "note": "Use returned boundary numbers before setting wall/inlet temperature.",
        },
        {"tool": "mesh_create", "args": {}},
        {"tool": "study_solve", "args": {"wait": False}},
        {
            "tool": "results_global_evaluate",
            "args": {"expression": "maxop1(T)", "unit": "K"},
            "note": "Example scalar result. Real expressions depend on created operators.",
        },
        {
            "tool": "results_export_image",
            "args": {"node_name": None, "file_path": str(OUT_DIR / "temperature_field.png")},
            "note": "Requires a plot/export node in the model.",
        },
    ])
    return calls


def print_plan() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plan = {
        "demo": "mini_heat_exchanger_mcp_demo",
        "parameters": asdict(DEMO_PARAMETERS),
        "tool_calls": demo_tool_plan(),
    }
    (OUT_DIR / "result_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    print(f"\nSaved dry-run plan: {OUT_DIR / 'result_plan.json'}")


async def call_tool(session: Any, name: str, args: dict[str, Any]) -> Any:
    result = await session.call_tool(name, args)
    payload: list[Any] = []
    for item in result.content:
        text = getattr(item, "text", None)
        if text is None:
            payload.append(str(item))
            continue
        try:
            payload.append(json.loads(text))
        except json.JSONDecodeError:
            payload.append(text)
    return payload[0] if len(payload) == 1 else payload


async def check_mcp() -> None:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            status = await call_tool(session, "comsol_status", {})
            workflow = await call_tool(session, "docs_get", {"topic": "workflow"})
            print(f"MCP tools available: {len(tools.tools)}")
            print("Status:")
            print(json.dumps(status, ensure_ascii=False, indent=2))
            print("Workflow doc loaded:", bool(workflow.get("success") if isinstance(workflow, dict) else workflow))


async def execute_demo(start_comsol: bool, connect_port: int | None) -> None:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    transcript: list[dict[str, Any]] = []
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if connect_port is not None:
                startup = {"tool": "comsol_connect", "args": {"port": connect_port, "host": "localhost"}}
            elif start_comsol:
                startup = {"tool": "comsol_start", "args": {"cores": 2, "version": None}}
            else:
                raise SystemExit("Use --start-comsol or --connect-port PORT with --execute.")

            for call in [startup] + demo_tool_plan():
                name = call["tool"]
                args = call["args"]
                print(f">>> {name} {args}")
                response = await call_tool(session, name, args)
                transcript.append({"tool": name, "args": args, "response": response})
                print(json.dumps(response, ensure_ascii=False, indent=2)[:2000])

                # Stop after boundary discovery. Boundary numbers must be reviewed before solving.
                if name == "physics_interactive_setup_heat":
                    print("\nPaused after boundary discovery. Review boundary numbers before solving/exporting.")
                    break

    (OUT_DIR / "mcp_transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved transcript: {OUT_DIR / 'mcp_transcript.json'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mini heat-exchanger COMSOL MCP demo.")
    parser.add_argument("--dry-run", action="store_true", help="Print and save the planned MCP tool calls.")
    parser.add_argument("--check-mcp", action="store_true", help="Verify MCP server responds without starting COMSOL.")
    parser.add_argument("--execute", action="store_true", help="Actually call COMSOL-backed MCP tools.")
    parser.add_argument("--start-comsol", action="store_true", help="Start a local COMSOL session before executing.")
    parser.add_argument("--connect-port", type=int, default=None, help="Connect to an existing COMSOL server port.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check_mcp:
        asyncio.run(check_mcp())
    elif args.execute:
        asyncio.run(execute_demo(args.start_comsol, args.connect_port))
    else:
        print_plan()


if __name__ == "__main__":
    main()

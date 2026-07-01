from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

server = Server("healthlink-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="find_nearby_clinics",
            description="Find nearby health clinics and doctors based on zip code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "zip_code": {"type": "string", "description": "The zip code to search"}
                },
                "required": ["zip_code"]
            }
        ),
        types.Tool(
            name="get_first_aid_steps",
            description="Get basic first aid steps for a given condition.",
            inputSchema={
                "type": "object",
                "properties": {
                    "condition": {"type": "string", "description": "The medical condition or injury"}
                },
                "required": ["condition"]
            }
        ),
        types.Tool(
            name="check_symptom_severity",
            description="Check the typical severity of a reported symptom.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symptom": {"type": "string", "description": "The reported symptom"}
                },
                "required": ["symptom"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "find_nearby_clinics":
        zip_code = arguments.get("zip_code", "")
        result = f"Found clinics near {zip_code}: City Health, UrgentCare, and Main St Medical."
        return [types.TextContent(type="text", text=result)]
    elif name == "get_first_aid_steps":
        condition = arguments.get("condition", "")
        result = f"Standard first aid steps for {condition}: Keep the person calm, check breathing, and seek medical help if severe."
        return [types.TextContent(type="text", text=result)]
    elif name == "check_symptom_severity":
        symptom = arguments.get("symptom", "")
        result = f"Symptom '{symptom}' usually requires professional medical evaluation."
        return [types.TextContent(type="text", text=result)]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

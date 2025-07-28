import logging

from langchain_neo4j import Neo4jGraph

from src.app.tools.tool_registry import tool_registry

logging.basicConfig(level=logging.INFO)


def resolve_tool(tool_name: str, args: dict) -> dict:
    if tool_name not in tool_registry:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool_def = tool_registry[tool_name]
    fn = tool_def["func"]
    input_keys = tool_def.get("args", [])
    filtered_args = {k: args[k] for k in input_keys if k in args}

    return fn(**filtered_args)


def tool_to_openai_function(tool_obj):
    args = tool_obj.args
    properties = {}
    required = []
    for k, v in args.items():
        properties[k] = {
            "type": v.get("type"),
            "description": v.get("description"),
        }
        if "default" not in v or v["default"] is None:
            required.append(k)
    return {
        "type": "function",
        "function": {
            "name": tool_obj.name,
            "description": tool_obj.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
        "strict": True,
    }


def neo4j_connect(env: str = "openwebui", enhanced_schema: bool = False):
    url = "bolt://neo4j-gds-apoc-n10s:7687" if env == "openwebui" else "bolt://localhost:7687"
    graph = Neo4jGraph(
        url=url,
        username="neo4j",
        password="neo4jpassword",
        enhanced_schema=enhanced_schema,
        sanitize=True,
    )
    return graph
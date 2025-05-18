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

from fastapi import APIRouter, HTTPException

from app.mcp.registry import get_tool_schema, list_tools

router = APIRouter()


@router.get("/tools")
def get_tools() -> dict[str, list[str]]:
    return {"tools": list_tools()}


@router.get("/tools/{tool_name}")
def get_tool(tool_name: str):
    schema = get_tool_schema(tool_name)
    if not schema:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {
        "tool": schema.name,
        "input_schema": schema.input_schema,
        "output_schema": schema.output_schema,
    }

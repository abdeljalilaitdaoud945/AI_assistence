from fastmcp import FastMCP
from services.calendar_service import (
    get_events,
    create_event,
    delete_event,
    list_upcoming_events,
)

mcp = FastMCP(name="InptApp2")

@mcp.tool
def mcp_get_events(date: str) -> str:
    return get_events(date)

@mcp.tool
def mcp_create_event(title: str, date: str, start_time: str, end_time: str) -> str:
    return create_event(title, date, start_time, end_time)

@mcp.tool
def mcp_delete_event(event_id: str) -> str:
    return delete_event(event_id)

@mcp.tool
def mcp_list_upcoming(max_results: int = 10) -> str:
    return list_upcoming_events(max_results)

if __name__ == "__main__":
    mcp.run()
from mcp.server.mcpserver import MCPServer
from src.tools.workspace import register_workspace_tools
from src.tools.drawing import register_drawing_tools
from src.tools.joinery import register_joinery_tools
from src.tools.inspector import register_inspector_tools

mcp = MCPServer("SketchUp_CNC_Controller")

register_workspace_tools(mcp)
register_drawing_tools(mcp)
register_joinery_tools(mcp)
register_inspector_tools(mcp)

if __name__ == "__main__":
    mcp.run()

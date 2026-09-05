from src.utils.sketchup_client import send_ruby_command
from mcp.server.mcpserver import MCPServer

def register_workspace_tools(mcp: MCPServer):
    @mcp.tool()
    def clear_workspace() -> str:
        """Clears the current SketchUp workspace by deleting all entities."""
        ruby_command = "Sketchup.active_model.entities.clear!; 'Workspace Cleared'"
        return f"Execution result: {send_ruby_command(ruby_command)}"

    @mcp.tool()
    def execute_custom_ruby(ruby_script: str) -> str:
        """Executes a custom generated Ruby script."""
        return send_ruby_command(ruby_script.strip())

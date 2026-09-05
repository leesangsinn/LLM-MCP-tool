from src.utils.sketchup_client import send_ruby_command, load_ruby_script
from mcp.server.mcpserver import MCPServer

def register_inspector_tools(mcp: MCPServer):
    @mcp.tool()
    def inspect_abf_data() -> str:
        """
        Hacks into ABF by scanning attribute dictionaries of a selected panel 
        and listing all ABF-related Ruby modules running in SketchUp memory.
        Returns data in JSON format.
        """
        script = load_ruby_script('inspect_abf_data')
        return send_ruby_command(script.strip())

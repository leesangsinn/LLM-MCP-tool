from src.utils.sketchup_client import send_ruby_command, load_ruby_script
from mcp.server.mcpserver import MCPServer
import json
from src.utils.cabinet_math import CabinetCalculator

def register_drawing_tools(mcp: MCPServer):
    @mcp.tool()
    def draw_cnc_part(
        part_name: str, width: float, depth: float, thickness: float = 17.0,
        pos_x: float = 0.0, pos_y: float = 0.0, pos_z: float = 0.0
    ) -> str:
        """Generates and places a single 3D CNC part using robust Origin-Transform logic."""
        script = load_ruby_script('draw_cnc_part')
        script = script.replace('{{part_name}}', part_name)\
                       .replace('{{width}}', str(width))\
                       .replace('{{depth}}', str(depth))\
                       .replace('{{thickness}}', str(thickness))\
                       .replace('{{pos_x}}', str(pos_x))\
                       .replace('{{pos_y}}', str(pos_y))\
                       .replace('{{pos_z}}', str(pos_z))
        return send_ruby_command(script.strip())

    @mcp.tool()
    def draw_basic_cabinet(
        width: float, height: float, depth: float, thickness: float = 17.0,
        back_thickness: float = 6.0, pos_x: float = 0.0, pos_y: float = 0.0, pos_z: float = 0.0
    ) -> str:
        """Constructs a complete basic cabinet box using the DRY robust draw_panel approach."""
        script = load_ruby_script('draw_basic_cabinet')
        script = script.replace('{{width}}', str(width))\
                       .replace('{{height}}', str(height))\
                       .replace('{{depth}}', str(depth))\
                       .replace('{{thickness}}', str(thickness))\
                       .replace('{{back_thickness}}', str(back_thickness))\
                       .replace('{{pos_x}}', str(pos_x))\
                       .replace('{{pos_y}}', str(pos_y))\
                       .replace('{{pos_z}}', str(pos_z))
        return send_ruby_command(script.strip())

    @mcp.tool()
    def draw_smart_cabinet(layout_json: str) -> str:
        """
        Takes a JSON layout definition, calculates absolute math using CabinetCalculator,
        and generates the full cabinet assembly in SketchUp via Ruby.
        """
        try:
            layout_data = json.loads(layout_json)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON - {str(e)}"
            
        calculator = CabinetCalculator(layout_data)
        parts_list = calculator.generate_parts()
        
        # Serialize back to tight JSON for Ruby
        parts_json = json.dumps(parts_list)
        
        script = load_ruby_script('draw_smart_assembly')
        script = script.replace('{{parts_json}}', parts_json)
        return send_ruby_command(script.strip())

    @mcp.tool()
    def insert_component_from_registry(
        component_id: str, pos_x: float, pos_y: float, pos_z: float,
        target_width: float, target_height: float, target_depth: float, color_hex: str = ""
    ) -> str:
        """
        Inserts a dynamic component (like a drawer) from a predefined registry.
        Automatically handles dynamic attributes and avoids hard-coded caching issues.
        """
        script = load_ruby_script('insert_component_from_registry')
        script = script.replace('{{component_id}}', component_id)\
                       .replace('{{pos_x}}', str(pos_x))\
                       .replace('{{pos_y}}', str(pos_y))\
                       .replace('{{pos_z}}', str(pos_z))\
                       .replace('{{target_width}}', str(target_width))\
                       .replace('{{target_height}}', str(target_height))\
                       .replace('{{target_depth}}', str(target_depth))\
                       .replace('{{color_hex}}', color_hex)
        return send_ruby_command(script.strip())


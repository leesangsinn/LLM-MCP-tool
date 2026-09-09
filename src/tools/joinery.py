from src.utils.sketchup_client import send_ruby_command, load_ruby_script
from mcp.server.mcpserver import MCPServer

def register_joinery_tools(mcp: MCPServer):
    @mcp.tool()
    def detect_joinery() -> str:
        """
        Detects panel intersections in the SketchUp model to locate Cams and Hinges.
        Returns a JSON string of detected joints and coordinates without inserting them.
        """
        script = load_ruby_script('detect_joinery')
        return send_ruby_command(script.strip())

    @mcp.tool()
    def auto_insert_hinges() -> str:
        """
        Automatically detects panel intersections and inserts ABF Hinges.
        """
        script = load_ruby_script('auto_insert_hinges')
        return send_ruby_command(script.strip())

    @mcp.tool()
    def auto_insert_minifix(joinery_type: str = "minifix", minifix_face: str = "bottom", minifix_distance: float = 50.0, d5_z_offset: float = 2.5) -> str:
        """
        Automatically detects panel intersections and inserts ABF Cam-locks or Shelf Pins.
        - joinery_type: "minifix" (Ốc cam + Chốt gỗ) or "d5" (Chỉ chốt đợt D5)
        - minifix_face: "bottom" (mặt dưới) or "top" (mặt trên)
        - minifix_distance: Khoảng cách từ mép trước/sau đợt đến lỗ khoan (mặc định 50mm).
        - d5_z_offset: Khoảng cách từ mặt đợt đến tâm lỗ chốt D5 (mặc định 2.5mm để kê khít đợt).
        """
        face_z_idx = 4 if minifix_face.lower() == "top" else 0
        cam_y_dir = -1 if minifix_face.lower() == "top" else 1
        draw_cam = "true" if joinery_type.lower() == "minifix" else "false"
        
        script = load_ruby_script('auto_insert_minifix')
        script = script.replace('{{minifix_distance}}', str(minifix_distance))\
                       .replace('{{face_z_idx}}', str(face_z_idx))\
                       .replace('{{cam_y_dir}}', str(cam_y_dir))\
                       .replace('{{draw_cam}}', draw_cam)\
                       .replace('{{d5_z_offset}}', str(d5_z_offset))
        
        return send_ruby_command(script.strip())

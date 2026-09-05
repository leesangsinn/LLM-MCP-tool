import os

os.makedirs('src/ruby_scripts', exist_ok=True)
os.makedirs('src/tools', exist_ok=True)
os.makedirs('src/utils', exist_ok=True)

utils_code = """import socket
import os

def load_ruby_script(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), '..', 'ruby_scripts', f'{name}.rb')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def send_ruby_command(ruby_script: str) -> str:
    HOST = '127.0.0.1'
    PORT = 8080
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((HOST, PORT))
            
            clean_script = ruby_script.replace('\\r', '')
            s.sendall(clean_script.encode('utf-8'))
            s.shutdown(socket.SHUT_WR)
            
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk: break
                response += chunk
            return response.decode('utf-8')
    except ConnectionRefusedError:
        return f"Error: Connection refused. Is SketchUp running and listening on {HOST}:{PORT}?"
    except socket.timeout:
        return "Error: Connection timed out after 5 seconds."
    except Exception as e:
        return f"Error: An unexpected network error occurred - {str(e)}"
"""
with open('src/utils/sketchup_client.py', 'w', encoding='utf-8') as f:
    f.write(utils_code)

def extract_between(text, start, end):
    return text.split(start)[1].split(end)[0].strip()

with open('src/server.py', encoding='utf-8') as f:
    server_code = f.read()

# 1. Workspace
workspace_py = """from utils.sketchup_client import send_ruby_command
from mcp.server.mcpserver import MCPServer

def register_workspace_tools(mcp: MCPServer):
    @mcp.tool()
    def clear_workspace() -> str:
        \"\"\"Clears the current SketchUp workspace by deleting all entities.\"\"\"
        ruby_command = "Sketchup.active_model.entities.clear!; 'Workspace Cleared'"
        return f"Execution result: {send_ruby_command(ruby_command)}"

    @mcp.tool()
    def execute_custom_ruby(ruby_script: str) -> str:
        \"\"\"Executes a custom generated Ruby script.\"\"\"
        return send_ruby_command(ruby_script.strip())
"""
with open('src/tools/workspace.py', 'w', encoding='utf-8') as f:
    f.write(workspace_py)


# 2. Drawing
draw_cnc_part_rb = extract_between(server_code, "Draw CNC Part: {part_name}', true)", "return send_ruby_command")
draw_cnc_part_rb = "  model.start_operation('Draw CNC Part: {{part_name}}', true)\n" + draw_cnc_part_rb.rsplit('"""', 1)[0].strip()
draw_cnc_part_rb = draw_cnc_part_rb.replace("{width}", "{{width}}").replace("{depth}", "{{depth}}").replace("{thickness}", "{{thickness}}").replace("{pos_x}", "{{pos_x}}").replace("{pos_y}", "{{pos_y}}").replace("{pos_z}", "{{pos_z}}")

draw_basic_cabinet_rb = extract_between(server_code, "def draw_panel(", "return send_ruby_command")
draw_basic_cabinet_rb = "def draw_panel(" + draw_basic_cabinet_rb.rsplit('"""', 1)[0].strip()
draw_basic_cabinet_rb = draw_basic_cabinet_rb.replace("{width}", "{{width}}").replace("{height}", "{{height}}").replace("{depth}", "{{depth}}").replace("{thickness}", "{{thickness}}").replace("{back_thickness}", "{{back_thickness}}").replace("{pos_x}", "{{pos_x}}").replace("{pos_y}", "{{pos_y}}").replace("{pos_z}", "{{pos_z}}")

with open('src/ruby_scripts/draw_cnc_part.rb', 'w', encoding='utf-8') as f:
    f.write("begin\n  model = Sketchup.active_model\n" + draw_cnc_part_rb)
with open('src/ruby_scripts/draw_basic_cabinet.rb', 'w', encoding='utf-8') as f:
    f.write(draw_basic_cabinet_rb)

drawing_py = """from utils.sketchup_client import send_ruby_command, load_ruby_script
from mcp.server.mcpserver import MCPServer

def register_drawing_tools(mcp: MCPServer):
    @mcp.tool()
    def draw_cnc_part(
        part_name: str, width: float, depth: float, thickness: float = 17.0,
        pos_x: float = 0.0, pos_y: float = 0.0, pos_z: float = 0.0
    ) -> str:
        \"\"\"Generates and places a single 3D CNC part using robust Origin-Transform logic.\"\"\"
        script = load_ruby_script('draw_cnc_part')
        script = script.replace('{{part_name}}', part_name)\\
                       .replace('{{width}}', str(width))\\
                       .replace('{{depth}}', str(depth))\\
                       .replace('{{thickness}}', str(thickness))\\
                       .replace('{{pos_x}}', str(pos_x))\\
                       .replace('{{pos_y}}', str(pos_y))\\
                       .replace('{{pos_z}}', str(pos_z))
        return send_ruby_command(script.strip())

    @mcp.tool()
    def draw_basic_cabinet(
        width: float, height: float, depth: float, thickness: float = 17.0,
        back_thickness: float = 6.0, pos_x: float = 0.0, pos_y: float = 0.0, pos_z: float = 0.0
    ) -> str:
        \"\"\"Constructs a complete basic cabinet box using the DRY robust draw_panel approach.\"\"\"
        script = load_ruby_script('draw_basic_cabinet')
        script = script.replace('{{width}}', str(width))\\
                       .replace('{{height}}', str(height))\\
                       .replace('{{depth}}', str(depth))\\
                       .replace('{{thickness}}', str(thickness))\\
                       .replace('{{back_thickness}}', str(back_thickness))\\
                       .replace('{{pos_x}}', str(pos_x))\\
                       .replace('{{pos_y}}', str(pos_y))\\
                       .replace('{{pos_z}}', str(pos_z))
        return send_ruby_command(script.strip())
"""
with open('src/tools/drawing.py', 'w', encoding='utf-8') as f:
    f.write(drawing_py)


# 3. Joinery
detect_joinery_rb = extract_between(server_code, "def detect_joinery() -> str:", "return send_ruby_command").split('ruby_script = """')[1].rsplit('"""', 1)[0].strip()
auto_insert_hinges_rb = extract_between(server_code, "def auto_insert_hinges() -> str:", "return send_ruby_command").split('ruby_script = """')[1].rsplit('"""', 1)[0].strip()
auto_insert_minifix_rb = extract_between(server_code, "def auto_insert_minifix(", "return send_ruby_command").split('ruby_script = """')[1].rsplit('"""', 1)[0].strip()

# Clean up string concatenation in minifix
auto_insert_minifix_rb = auto_insert_minifix_rb.replace('""" + str(minifix_distance) + """.mm', '{{minifix_distance}}.mm')
auto_insert_minifix_rb = auto_insert_minifix_rb.replace('""" + str(face_z_idx) + """', '{{face_z_idx}}')
auto_insert_minifix_rb = auto_insert_minifix_rb.replace('""" + str(cam_y_dir) + """', '{{cam_y_dir}}')
auto_insert_minifix_rb = auto_insert_minifix_rb.replace('""" + draw_cam + """', '{{draw_cam}}')

with open('src/ruby_scripts/detect_joinery.rb', 'w', encoding='utf-8') as f:
    f.write(detect_joinery_rb)
with open('src/ruby_scripts/auto_insert_hinges.rb', 'w', encoding='utf-8') as f:
    f.write(auto_insert_hinges_rb)
with open('src/ruby_scripts/auto_insert_minifix.rb', 'w', encoding='utf-8') as f:
    f.write(auto_insert_minifix_rb)

joinery_py = """from utils.sketchup_client import send_ruby_command, load_ruby_script
from mcp.server.mcpserver import MCPServer

def register_joinery_tools(mcp: MCPServer):
    @mcp.tool()
    def detect_joinery() -> str:
        \"\"\"
        Detects panel intersections in the SketchUp model to locate Cams and Hinges.
        Returns a JSON string of detected joints and coordinates without inserting them.
        \"\"\"
        script = load_ruby_script('detect_joinery')
        return send_ruby_command(script.strip())

    @mcp.tool()
    def auto_insert_hinges() -> str:
        \"\"\"
        Automatically detects panel intersections and inserts ABF Hinges.
        \"\"\"
        script = load_ruby_script('auto_insert_hinges')
        return send_ruby_command(script.strip())

    @mcp.tool()
    def auto_insert_minifix(joinery_type: str = "minifix", minifix_face: str = "bottom", minifix_distance: float = 50.0) -> str:
        \"\"\"
        Automatically detects panel intersections and inserts ABF Cam-locks or Shelf Pins.
        - joinery_type: "minifix" (Ốc cam + Chốt gỗ) or "d5" (Chỉ chốt đợt D5)
        - minifix_face: "bottom" (mặt dưới) or "top" (mặt trên)
        - minifix_distance: Khoảng cách từ mép trước/sau đợt đến lỗ khoan (mặc định 50mm).
        \"\"\"
        face_z_idx = 4 if minifix_face.lower() == "top" else 0
        cam_y_dir = -1 if minifix_face.lower() == "top" else 1
        draw_cam = "true" if joinery_type.lower() == "minifix" else "false"
        
        script = load_ruby_script('auto_insert_minifix')
        script = script.replace('{{minifix_distance}}', str(minifix_distance))\\
                       .replace('{{face_z_idx}}', str(face_z_idx))\\
                       .replace('{{cam_y_dir}}', str(cam_y_dir))\\
                       .replace('{{draw_cam}}', draw_cam)
        
        return send_ruby_command(script.strip())
"""
with open('src/tools/joinery.py', 'w', encoding='utf-8') as f:
    f.write(joinery_py)


# 4. Inspector
inspect_abf_data_rb = extract_between(server_code, "def inspect_abf_data() -> str:", "return send_ruby_command").split('ruby_script = """')[1].rsplit('"""', 1)[0].strip()
with open('src/ruby_scripts/inspect_abf_data.rb', 'w', encoding='utf-8') as f:
    f.write(inspect_abf_data_rb)

inspector_py = """from utils.sketchup_client import send_ruby_command, load_ruby_script
from mcp.server.mcpserver import MCPServer

def register_inspector_tools(mcp: MCPServer):
    @mcp.tool()
    def inspect_abf_data() -> str:
        \"\"\"
        Hacks into ABF by scanning attribute dictionaries of a selected panel 
        and listing all ABF-related Ruby modules running in SketchUp memory.
        Returns data in JSON format.
        \"\"\"
        script = load_ruby_script('inspect_abf_data')
        return send_ruby_command(script.strip())
"""
with open('src/tools/inspector.py', 'w', encoding='utf-8') as f:
    f.write(inspector_py)

# 5. Main server.py
new_server_py = """from mcp.server.mcpserver import MCPServer
from tools.workspace import register_workspace_tools
from tools.drawing import register_drawing_tools
from tools.joinery import register_joinery_tools
from tools.inspector import register_inspector_tools

mcp = MCPServer("SketchUp_CNC_Controller")

register_workspace_tools(mcp)
register_drawing_tools(mcp)
register_joinery_tools(mcp)
register_inspector_tools(mcp)

if __name__ == "__main__":
    mcp.run()
"""
with open('src/server.py', 'w', encoding='utf-8') as f:
    f.write(new_server_py)

print("Extraction completed!")

from mcp.server.mcpserver import MCPServer
import socket

# Initialize the MCPServer
mcp = MCPServer("SketchUp_CNC_Controller")

def send_ruby_command(ruby_script: str) -> str:
    """
    Helper function to send Ruby commands to the SketchUp instance via TCP Socket.
    """
    HOST = '127.0.0.1'
    PORT = 8080

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((HOST, PORT))
            
            # Gửi script dạng UTF-8
            s.sendall(ruby_script.encode('utf-8'))
            s.shutdown(socket.SHUT_WR) # ĐÓNG CỔNG GỬI ĐỂ RUBY BIẾT ĐÃ HẾT LỆNH

            # Nâng cấp: Vòng lặp nhận dữ liệu để tránh mất gói tin dài
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            
            return response.decode('utf-8')

    except ConnectionRefusedError:
        return f"Error: Connection refused. Is SketchUp running and listening on {HOST}:{PORT}?"
    except socket.timeout:
        return f"Error: Connection timed out after 5 seconds."
    except Exception as e:
        return f"Error: An unexpected network error occurred - {str(e)}"


@mcp.tool()
def clear_workspace() -> str:
    """Clears the current SketchUp workspace by deleting all entities."""
    ruby_command = "Sketchup.active_model.entities.clear!; 'Workspace Cleared'"
    return f"Execution result: {send_ruby_command(ruby_command)}"


@mcp.tool()
def draw_cnc_part(
    part_name: str, width: float, depth: float, thickness: float = 17.0,
    pos_x: float = 0.0, pos_y: float = 0.0, pos_z: float = 0.0
) -> str:
    """Generates and places a single 3D CNC part using robust Origin-Transform logic."""
    ruby_script = f"""
begin
  model = Sketchup.active_model
  model.start_operation('Draw CNC Part: {part_name}', true)
  ents = model.active_entities

  # Vẽ tại gốc tọa độ
  group = ents.add_group
  pt1 = Geom::Point3d.new(0, 0, 0)
  pt2 = Geom::Point3d.new({width}.mm, 0, 0)
  pt3 = Geom::Point3d.new({width}.mm, {depth}.mm, 0)
  pt4 = Geom::Point3d.new(0, {depth}.mm, 0)
  
  face = group.entities.add_face(pt1, pt2, pt3, pt4)
  face.pushpull(-{thickness}.mm) # Extrude (SketchUp mặc định kéo âm sẽ dựng hình lên trên chuẩn Normal)

  # Đóng gói và đặt tên
  instance = group.to_component
  instance.definition.name = '{part_name}'

  # Dời đến tọa độ đích
  tr = Geom::Transformation.translation(Geom::Vector3d.new({pos_x}.mm, {pos_y}.mm, {pos_z}.mm))
  instance.transform!(tr)

  model.commit_operation
  "Success: Part '{part_name}' created."
rescue => e
  model.abort_operation
  "Error: #{{e.message}}"
end
    """
    return send_ruby_command(ruby_script.strip())


@mcp.tool()
def draw_basic_cabinet(
    width: float, height: float, depth: float, thickness: float = 17.0,
    back_thickness: float = 6.0, pos_x: float = 0.0, pos_y: float = 0.0, pos_z: float = 0.0
) -> str:
    """Constructs a complete basic cabinet box using the DRY robust draw_panel approach."""
    ruby_script = f"""
begin
  model = Sketchup.active_model
  model.start_operation('Draw Basic Cabinet', true)
  ents = model.active_entities

  def draw_panel(ents, name, w, d, h, px, py, pz)
    group = ents.add_group
    pt1 = Geom::Point3d.new(0, 0, 0)
    pt2 = Geom::Point3d.new(w, 0, 0)
    pt3 = Geom::Point3d.new(w, d, 0)
    pt4 = Geom::Point3d.new(0, d, 0)
    
    face = group.entities.add_face(pt1, pt2, pt3, pt4)
    face.pushpull(-h)
    
    instance = group.to_component
    instance.definition.name = name
    
    tr = Geom::Transformation.translation(Geom::Vector3d.new(px, py, pz))
    instance.transform!(tr)
  end

  w = {width}.mm
  h = {height}.mm
  d = {depth}.mm
  t = {thickness}.mm
  bt = {back_thickness}.mm
  px = {pos_x}.mm
  py = {pos_y}.mm
  pz = {pos_z}.mm

  # Các tấm cấu tạo vỏ tủ
  draw_panel(ents, '[Vach_Trai]', t, d, h, px, py, pz)
  draw_panel(ents, '[Vach_Phai]', t, d, h, px + w - t, py, pz)
  draw_panel(ents, '[Day]', w - 2*t, d, t, px + t, py, pz)
  draw_panel(ents, '[Noc]', w - 2*t, d, t, px + t, py, pz + h - t)
  draw_panel(ents, '[Hau]', w - 2*t, bt, h - 2*t, px + t, py + d - bt, pz + t)

  model.commit_operation
  "Success: Basic cabinet {width}x{height}x{depth} created."
rescue => e
  model.abort_operation
  "Error: #{{e.message}}"
end
    """
    return send_ruby_command(ruby_script.strip())


@mcp.tool()
def execute_custom_ruby(ruby_script: str) -> str:
    """Executes a custom generated Ruby script."""
    return send_ruby_command(ruby_script.strip())


if __name__ == "__main__":
    mcp.run()
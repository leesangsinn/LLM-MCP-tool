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

@mcp.tool()
def detect_joinery() -> str:
    """
    Detects panel intersections in the SketchUp model to locate Cams and Hinges.
    Returns a JSON string of detected joints and coordinates without inserting them.
    """
    ruby_script = """
begin
  model = Sketchup.active_model
  entities = model.entities
  groups_and_comps = entities.grep(Sketchup::Group) + entities.grep(Sketchup::ComponentInstance)
  
  shelves = []
  vertical_panels = []
  doors = []

  # Phân loại cấu kiện
  groups_and_comps.each do |ent|
    bounds = ent.bounds
    dx = bounds.width.to_mm
    dy = bounds.height.to_mm
    dz = bounds.depth.to_mm
    
    if dz > 16 && dz < 19
      shelves << ent
    elsif dx > 16 && dx < 19
      vertical_panels << ent
    elsif dy > 16 && dy < 20
      doors << ent
    end
  end

  results = {
    cams: [],
    hinges: []
  }

  # Quét Cam Chốt
  shelves.each do |shelf|
    vertical_panels.each do |v_panel|
      if shelf.bounds.intersect(v_panel.bounds).valid?
        s_bounds = shelf.bounds
        v_bounds = v_panel.bounds
        
        intersect_x = v_bounds.center.x.to_mm
        start_y = s_bounds.corner(0).y.to_mm
        depth_y = s_bounds.height.to_mm
        bottom_z = s_bounds.corner(0).z.to_mm
        
        cam_z = bottom_z + 8.5
        
        results[:cams] << {x: intersect_x, y: start_y + 50, z: cam_z}
        results[:cams] << {x: intersect_x, y: start_y + depth_y - 50, z: cam_z}
        
        if depth_y >= 400
          results[:cams] << {x: intersect_x, y: start_y + (depth_y/2.0), z: cam_z}
        end
      end
    end
  end

  # Quét Bản Lề
  doors.each do |door|
    vertical_panels.each do |v_panel|
      if door.bounds.intersect(v_panel.bounds).valid?
        d_bounds = door.bounds
        door_height = d_bounds.depth.to_mm
        start_z = d_bounds.corner(0).z.to_mm
        hinge_x = (d_bounds.corner(0).x.to_mm) + 22
        hinge_y = d_bounds.corner(0).y.to_mm
        
        hinge_count = 2
        hinge_count = 3 if door_height > 1500
        hinge_count = 4 if door_height > 2000
        
        results[:hinges] << {x: hinge_x, y: hinge_y, z: start_z + 100}
        results[:hinges] << {x: hinge_x, y: hinge_y, z: start_z + door_height - 100}
        
        if hinge_count == 3
          results[:hinges] << {x: hinge_x, y: hinge_y, z: start_z + (door_height / 2.0)}
        elsif hinge_count == 4
          space = (door_height - 200) / 3.0
          results[:hinges] << {x: hinge_x, y: hinge_y, z: start_z + 100 + space}
          results[:hinges] << {x: hinge_x, y: hinge_y, z: start_z + 100 + (2 * space)}
        end
      end
    end
  end

  # Serialize to JSON manually since standard json library might not be in SketchUp Ruby by default
  cam_str = results[:cams].map{|c| %Q({"x":#{c[:x]},"y":#{c[:y]},"z":#{c[:z]}}) }.join(',')
  hinge_str = results[:hinges].map{|h| %Q({"x":#{h[:x]},"y":#{h[:y]},"z":#{h[:z]}}) }.join(',')
  
  "{\\\"cams\\\":[#{cam_str}], \\\"hinges\\\":[#{hinge_str}]}"
rescue => e
  "Error: #{e.message}"
end
    """
    return send_ruby_command(ruby_script.strip())

@mcp.tool()
def auto_insert_joinery() -> str:
    """
    Automatically detects panel intersections and inserts ABF Cam-locks and Hinges
    by cloning the user's previously placed template components.
    """
    ruby_script = """
begin
  model = Sketchup.active_model
  entities = model.entities
  
  # 1. Hàm dọn dẹp các bản lề mồi / bản lề thừa
  def cleanup_old_hardware(ents)
    ents.to_a.each do |e|
      if e.is_a?(Sketchup::ComponentInstance) || e.is_a?(Sketchup::Group)
        inst_name = e.respond_to?(:name) ? e.name : ""
        def_name = e.respond_to?(:definition) ? e.definition.name : ""
        
        is_abf = inst_name.start_with?("_ABF_hingeCup") || inst_name.start_with?("_ABF_hingeMountingPlate") || inst_name.start_with?("_ABF_minifix") ||
                 def_name.start_with?("_ABF_hingeCup") || def_name.start_with?("_ABF_hingeMountingPlate") || def_name.start_with?("_ABF_minifix")
                 
        if is_abf
          e.erase!
        else
          # Đệ quy vào các group/component bên trong
          target = e.respond_to?(:definition) ? e.definition.entities : e.entities
          cleanup_old_hardware(target)
        end
      end
    end
  end
  
  # Tự động tạo khuôn mới từ con số 0 (không cần mồi)
  def get_or_create_cup_template(model)
    def_name = "_ABF_hingeCup"
    d = model.definitions[def_name]
    d = model.definitions.add(def_name) if d.nil?
    d.entities.clear!
    # Lỗ Cup 35mm
    d.entities.add_circle(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(0, 0, 1), 17.5.mm)
    # 2 lỗ bắt vít của Cup (cách nhau 48mm)
    d.entities.add_circle(Geom::Point3d.new(0, 24.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
    d.entities.add_circle(Geom::Point3d.new(0, -24.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
    d
  end

  def get_or_create_plate_template(model)
    def_name = "_ABF_hingeMountingPlate"
    d = model.definitions[def_name]
    d = model.definitions.add(def_name) if d.nil?
    d.entities.clear!
    # Đế bản lề chỉ có 2 lỗ vít (cách nhau 32mm)
    d.entities.add_circle(Geom::Point3d.new(0, 16.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
    d.entities.add_circle(Geom::Point3d.new(0, -16.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
    d
  end

  model.start_operation('Auto Insert Joinery', true)

  # Dọn dẹp rác trước khi bắn
  cleanup_old_hardware(entities)

  templates = {}
  # Tạm bỏ qua Cam chốt
  templates[:cup] = get_or_create_cup_template(model)
  templates[:plate] = get_or_create_plate_template(model)

  # 2. Phân loại cấu kiện
  groups_and_comps = entities.grep(Sketchup::Group) + entities.grep(Sketchup::ComponentInstance)
  shelves, vertical_panels, doors = [], [], []

  groups_and_comps.each do |ent|
    bounds = ent.bounds
    dx, dy, dz = bounds.width.to_mm, bounds.height.to_mm, bounds.depth.to_mm
    name = ent.respond_to?(:name) ? ent.name.downcase : ""
    
    if dz > 16 && dz < 19
      shelves << ent
    elsif dx > 16 && dx < 19
      vertical_panels << ent
    elsif dy > 16 && dy < 20
      # Lọc Hậu, Mặt ngăn kéo, và Len chân (dz quá nhỏ) khỏi danh sách Cánh tủ
      if name.include?("hau") || name.include?("back") || bounds.center.y > 200.mm || name.include?("keo") || name.include?("drawer") || name.include?("nk") || dz < 300
        # Bỏ qua
      else
        doors << ent
      end
    end
  end

  count = 0

  # 3. Quét Cam Chốt và Clone (TẠM THỜI BỎ QUA THEO YÊU CẦU)
  # shelves.each do |shelf|
  #   vertical_panels.each do |v_panel|
  #     if shelf.bounds.intersect(v_panel.bounds).valid?
  #       s_bounds, v_bounds = shelf.bounds, v_panel.bounds
  #       intersect_x = v_bounds.center.x
  #       start_y = s_bounds.corner(0).y
  #       depth_y = s_bounds.height
  #       
  #       is_left_panel = (intersect_x < s_bounds.center.x)
  #       
  #       # Tọa độ gốc ABF: X nằm chính xác tại mặt vách hồi, Z/Y nằm trên đợt
  #       cam_x = is_left_panel ? v_bounds.corner(1).x : v_bounds.corner(0).x
  #       cam_z = s_bounds.corner(4).z # Trên mặt đợt
  #       
  #       y_points = [start_y + 50.mm, start_y + depth_y - 50.mm]
  #       y_points << start_y + (depth_y / 2.0) if depth_y.to_mm >= 400
  #       
  #       # Trục Z của Cam đâm vào vách hồi (-X hoặc +X)
  #       cam_z_vec = is_left_panel ? Geom::Vector3d.new(-1, 0, 0) : Geom::Vector3d.new(1, 0, 0)
  #       # Trục X của Cam dọc theo chiều sâu đợt (+Y)
  #       cam_x_vec = Geom::Vector3d.new(0, 1, 0)
  #       cam_y_vec = cam_z_vec * cam_x_vec
  #
  #       y_points.each do |py|
  #         origin = Geom::Point3d.new(cam_x, py, cam_z)
  #         tr = Geom::Transformation.axes(origin, cam_x_vec, cam_y_vec, cam_z_vec)
  #         inst = entities.add_instance(templates[:cam], tr)
  #         inst.name = "_ABF_minifixPlasticBase"
  #         count += 1
  #       end
  #     end
  #   end
  # end

  # 4. Quét Bản lề và Clone (Dùng khe hở thay vì intersect)
  doors.each do |door|
    vertical_panels.each do |v_panel|
      d_bounds = door.bounds
      v_bounds = v_panel.bounds
      
      is_left_hinge = (v_bounds.center.x < d_bounds.center.x)
      
      door_edge_x = is_left_hinge ? d_bounds.corner(0).x : d_bounds.corner(1).x
      panel_inner_x = is_left_hinge ? v_bounds.corner(1).x : v_bounds.corner(0).x
      panel_outer_x = is_left_hinge ? v_bounds.corner(0).x : v_bounds.corner(1).x

      gap_inset = (door_edge_x - panel_inner_x).abs
      gap_overlay = (door_edge_x - panel_outer_x).abs

      if gap_inset < 3.mm || gap_overlay < 3.mm
        door_height = d_bounds.depth
        start_z = d_bounds.corner(0).z
        
        # Tọa độ Y: Đế bản lề luôn lùi 37mm tính từ MẶT TRONG CỦA CÁNH TỦ (cup_y)
        cup_y = d_bounds.corner(0).y + d_bounds.height
        plate_y = cup_y + 37.mm 

        # Tọa độ X:
        cup_x = is_left_hinge ? (door_edge_x + 22.mm) : (door_edge_x - 22.mm)
        plate_x = panel_inner_x
        
        h_mm = door_height.to_mm
        hinge_count = 2
        hinge_count = 3 if h_mm > 1500
        hinge_count = 4 if h_mm > 2000
        
        z_points = [start_z + 100.mm, start_z + door_height - 100.mm]
        if hinge_count == 3
          z_points << start_z + (door_height / 2.0)
        elsif hinge_count == 4
          space = (door_height - 200.mm) / 3.0
          z_points << start_z + 100.mm + space
          z_points << start_z + 100.mm + (2.0 * space)
        end
        
        # Cup:
        cup_z_vec = Geom::Vector3d.new(0, 1, 0) # Đâm vào thịt cánh
        cup_y_vec = Geom::Vector3d.new(0, 0, 1) # Hướng lên trời (Lỗ vít dọc)
        cup_x_vec = cup_y_vec * cup_z_vec # (-1, 0, 0)

        # Plate:
        plate_z_vec = is_left_hinge ? Geom::Vector3d.new(-1, 0, 0) : Geom::Vector3d.new(1, 0, 0) # Đâm vào vách hồi
        plate_y_vec = Geom::Vector3d.new(0, 0, 1) # Hướng lên trời (Lỗ vít dọc)
        plate_x_vec = plate_y_vec * plate_z_vec

        z_points.each do |hz|
          # Gắn Cup vào trong Group/Component của Cánh tủ
          if templates[:cup]
            c_origin = Geom::Point3d.new(cup_x, cup_y, hz)
            c_tr = Geom::Transformation.axes(c_origin, cup_x_vec, cup_y_vec, cup_z_vec)
            
            door.make_unique if door.is_a?(Sketchup::ComponentInstance)
            c_target = door.respond_to?(:definition) ? door.definition.entities : door.entities
            local_c_tr = door.transformation.inverse * c_tr
            
            c_inst = c_target.add_instance(templates[:cup], local_c_tr)
            c_inst.name = "_ABF_hingeCup"
            count += 1
          end
          
          # Gắn Plate vào trong Group/Component của Vách hồi
          if templates[:plate]
            p_origin = Geom::Point3d.new(plate_x, plate_y, hz)
            p_tr = Geom::Transformation.axes(p_origin, plate_x_vec, plate_y_vec, plate_z_vec)
            
            v_panel.make_unique if v_panel.is_a?(Sketchup::ComponentInstance)
            v_target = v_panel.respond_to?(:definition) ? v_panel.definition.entities : v_panel.entities
            local_p_tr = v_panel.transformation.inverse * p_tr
            
            p_inst = v_target.add_instance(templates[:plate], local_p_tr)
            p_inst.name = "_ABF_hingeMountingPlate"
            count += 1
          end
        end
      end
    end
  end

  model.commit_operation
  "Success: Auto-inserted #{count} hardware components using centered ABF templates."
rescue => e
  model.abort_operation
  "Error: #{e.message}"
end
    """
    return send_ruby_command(ruby_script.strip())


if __name__ == "__main__":
    mcp.run()
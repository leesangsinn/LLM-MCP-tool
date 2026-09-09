# 1. Hàm dọn dẹp các bản lề mồi / bản lề thừa
def cleanup_old_hardware(ents)
  ents.to_a.each do |e|
    if e.is_a?(Sketchup::ComponentInstance) || e.is_a?(Sketchup::Group)
      inst_name = e.respond_to?(:name) ? e.name : ""
      def_name = e.respond_to?(:definition) ? e.definition.name : ""
      
      is_abf = inst_name.start_with?("_ABF_hingeCup") || inst_name.start_with?("_ABF_hingeMountingPlate") ||
               def_name.start_with?("_ABF_hingeCup") || def_name.start_with?("_ABF_hingeMountingPlate")
               
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

def get_or_create_cup_template(model)
  def_name = "_ABF_hingeCup"
  d = model.definitions[def_name]
  return d if d && d.entities.length > 0 # Tôn trọng và giữ nguyên Component gốc của ABF
  
  d = model.definitions.add(def_name) if d.nil?
  d.entities.clear!
  # Lỗ Cup 35mm (Fallback nếu chưa có ABF)
  d.entities.add_circle(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(0, 0, 1), 17.5.mm)
  # 2 lỗ bắt vít của Cup (cách nhau 48mm)
  d.entities.add_circle(Geom::Point3d.new(0, 24.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
  d.entities.add_circle(Geom::Point3d.new(0, -24.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
  d
end

def get_or_create_plate_template(model)
  def_name = "_ABF_hingeMountingPlate"
  d = model.definitions[def_name]
  return d if d && d.entities.length > 0 # Tôn trọng ABF

  d = model.definitions.add(def_name) if d.nil?
  d.entities.clear!
  # Đế bản lề chỉ có 2 lỗ vít (cách nhau 32mm)
  d.entities.add_circle(Geom::Point3d.new(0, 16.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
  d.entities.add_circle(Geom::Point3d.new(0, -16.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
  d
end

begin
  model = Sketchup.active_model
  entities = model.entities
  model.start_operation('Auto Insert Hinges', true)
  
  active_ents = model.active_entities
  edit_tr_inv = model.edit_transform.inverse

  cleanup_old_hardware(active_ents)

  templates[:cup] = get_or_create_cup_template(model)
  templates[:plate] = get_or_create_plate_template(model)

  door_hardware_map = {}
  panel_hardware_map = {}

  count = 0

  # Lấy tất cả Group/Component trong model (quét toàn bộ)
  groups_and_comps = active_ents.grep(Sketchup::Group) + active_ents.grep(Sketchup::ComponentInstance)
  vertical_panels, doors = [], []

  groups_and_comps.each do |ent|
    bounds = ent.bounds
    dx, dy, dz = bounds.width.to_mm, bounds.height.to_mm, bounds.depth.to_mm
    name = ent.respond_to?(:name) ? ent.name.downcase : ""
    
    if dx > 16 && dx < 19
      ent.make_unique if ent.respond_to?(:make_unique)
      vertical_panels << ent
    elsif dy > 16 && dy < 20
      unless name.include?("hau") || name.include?("back") || bounds.center.y > 200.mm || name.include?("keo") || name.include?("drawer") || name.include?("nk") || dz < 300
        ent.make_unique if ent.respond_to?(:make_unique)
        doors << ent
      end
    end
  end
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
        
        # Tọa độ Y của Cup: Lùi vào từ mép ngoài cánh một khoảng bằng đúng độ dày cánh
        cup_y = d_bounds.corner(0).y + d_bounds.height
        
        # Tọa độ Y của Plate: Luôn cách mép trước của vách (front edge) đúng 37mm theo chuẩn
        plate_y = v_bounds.corner(0).y + 37.mm 

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
          # Gắn Cup
          if templates[:cup]
            c_origin = Geom::Point3d.new(cup_x, cup_y, hz)
            c_tr = Geom::Transformation.axes(c_origin, cup_x_vec, cup_y_vec, cup_z_vec)
            
            local_c_tr = edit_tr_inv * c_tr
            c_inst = active_ents.add_instance(templates[:cup], local_c_tr)
            c_inst.name = "_ABF_hingeCup"
            door_hardware_map[door] ||= []
            door_hardware_map[door] << c_inst
            count += 1
          end
          
          # Gắn Plate
          if templates[:plate]
            p_origin = Geom::Point3d.new(plate_x, plate_y, hz)
            p_tr = Geom::Transformation.axes(p_origin, plate_x_vec, plate_y_vec, plate_z_vec)
            
            local_p_tr = edit_tr_inv * p_tr
            p_inst = active_ents.add_instance(templates[:plate], local_p_tr)
            p_inst.name = "_ABF_hingeMountingPlate"
            panel_hardware_map[v_panel] ||= []
            panel_hardware_map[v_panel] << p_inst
            count += 1
          end
        end
      end
    end
  end

  # Thực hiện gom Group theo từng Cụm (Cánh + Cối) và (Vách + Đế)
  door_hardware_map.each do |door, hardware|
    if hardware.any?
      grp = active_ents.add_group([door] + hardware)
      original_name = door.respond_to?(:name) && !door.name.empty? ? door.name : door.definition.name
      grp.name = original_name
    end
  end

  panel_hardware_map.each do |v_panel, hardware|
    if hardware.any?
      grp = active_ents.add_group([v_panel] + hardware)
      original_name = v_panel.respond_to?(:name) && !v_panel.name.empty? ? v_panel.name : v_panel.definition.name
      grp.name = original_name
    end
  end

  model.commit_operation
  "Success: Auto-inserted #{count} hardware components using centered ABF templates."
rescue => e
  model.abort_operation
  "Error: #{e.message}"
end
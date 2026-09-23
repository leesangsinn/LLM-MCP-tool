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
        target = e.respond_to?(:definition) ? e.definition.entities : e.entities
        cleanup_old_hardware(target)
      end
    end
  end
end

def get_or_create_cup_template(model)
  def_name = "_ABF_hingeCup"
  d = model.definitions[def_name]
  return d if d && d.entities.length > 0 
  
  d = model.definitions.add(def_name) if d.nil?
  d.entities.clear!
  # Lỗ Cup 35mm
  d.entities.add_circle(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(0, 0, 1), 17.5.mm)
  # 2 lỗ bắt vít của Cup: Lệch X 7.mm, R=1.mm (đường kính 2mm)
  d.entities.add_circle(Geom::Point3d.new(7.mm, 24.mm, 0), Geom::Vector3d.new(0, 0, 1), 1.mm)
  d.entities.add_circle(Geom::Point3d.new(7.mm, -24.mm, 0), Geom::Vector3d.new(0, 0, 1), 1.mm)
  d
end

def get_or_create_plate_template(model)
  def_name = "_ABF_hingeMountingPlate"
  d = model.definitions[def_name]
  return d if d && d.entities.length > 0

  d = model.definitions.add(def_name) if d.nil?
  d.entities.clear!
  # Đế bản lề: Lỗ mồi R=1.mm (đường kính 2mm), cách nhau 32mm
  d.entities.add_circle(Geom::Point3d.new(0, 16.mm, 0), Geom::Vector3d.new(0, 0, 1), 1.mm)
  d.entities.add_circle(Geom::Point3d.new(0, -16.mm, 0), Geom::Vector3d.new(0, 0, 1), 1.mm)
  d
end

begin
  model = Sketchup.active_model
  entities = model.entities
  model.start_operation('Auto Insert Hinges', true)
  
  active_ents = model.active_entities
  edit_tr_inv = model.edit_transform.inverse

  cleanup_old_hardware(active_ents)

  templates = {}
  templates[:cup] = get_or_create_cup_template(model)
  templates[:plate] = get_or_create_plate_template(model)

  door_hardware_map = {}
  panel_hardware_map = {}
  panel_hinge_registry = {} # Đăng ký tọa độ Z chống đụng ốc vít

  count = 0

  groups_and_comps = active_ents.grep(Sketchup::Group) + active_ents.grep(Sketchup::ComponentInstance)
  vertical_panels, doors = [], []
  blocked_zones = []

  groups_and_comps.each do |ent|
    bounds = ent.bounds
    dx, dy, dz = bounds.width.to_mm, bounds.height.to_mm, bounds.depth.to_mm
    name = ent.respond_to?(:name) ? ent.name.downcase : ""
    
    if dx > 16 && dx < 19
      ent.make_unique if ent.respond_to?(:make_unique)
      vertical_panels << ent
    elsif dy > 16 && dy < 20
      unless name.include?("hau") || name.include?("back") || name.include?("keo") || name.include?("drawer") || name.include?("nk") || dz < 300
        ent.make_unique if ent.respond_to?(:make_unique)
        doors << ent
      end
    elsif dz < 25 && dx > 50 && dy > 50
      blocked_zones << { min_z: bounds.min.z - 25.mm, max_z: bounds.max.z + 25.mm }
    end
  end

  if vertical_panels.any?
    min_x_panel = vertical_panels.map { |p| p.bounds.center.x }.min
    max_x_panel = vertical_panels.map { |p| p.bounds.center.x }.max
    cabinet_center_x = (min_x_panel + max_x_panel) / 2.0

    doors.each do |door|
      candidate_panels = []
      
      vertical_panels.each do |v_panel|
        d_bounds = door.bounds
        v_bounds = v_panel.bounds
        
        is_left_hinge = (v_bounds.center.x < d_bounds.center.x)
        door_edge_x = is_left_hinge ? d_bounds.corner(0).x : d_bounds.corner(1).x
        
        panel_inner_x = is_left_hinge ? v_bounds.corner(1).x : v_bounds.corner(0).x
        panel_outer_x = is_left_hinge ? v_bounds.corner(0).x : v_bounds.corner(1).x
        
        p_min_x = [panel_inner_x, panel_outer_x].min
        p_max_x = [panel_inner_x, panel_outer_x].max

        # Hitbox Không Gian (Range) nới lỏng cho Cánh Phủ Nửa (Bản Lề B)
        if door_edge_x >= (p_min_x - 5.mm) && door_edge_x <= (p_max_x + 5.mm)
          candidate_panels << {
            panel: v_panel, 
            x: v_bounds.center.x, 
            is_left: is_left_hinge, 
            door_edge_x: door_edge_x, 
            panel_inner_x: panel_inner_x
          }
        end
      end

      if candidate_panels.any?
        is_left_side = door.bounds.center.x < cabinet_center_x
        
        best_candidate = if is_left_side
                           candidate_panels.min_by { |c| c[:x] }
                         else
                           candidate_panels.max_by { |c| c[:x] }
                         end
                         
        v_panel = best_candidate[:panel]
        is_left_hinge = best_candidate[:is_left]
        door_edge_x = best_candidate[:door_edge_x]
        panel_inner_x = best_candidate[:panel_inner_x]
        
        d_bounds = door.bounds
        v_bounds = v_panel.bounds
        
        door_height = d_bounds.depth
        start_z = d_bounds.corner(0).z
        
        inward_vector_y = v_bounds.center.y - d_bounds.center.y
        inward_dir = inward_vector_y > 0 ? 1 : -1

        panel_front_y = inward_dir > 0 ? v_bounds.min.y : v_bounds.max.y
        # Đế bản lề cách mép vách hồi đúng 34mm (Theo chuẩn ABF đo đạc)
        plate_y = panel_front_y + (34.mm * inward_dir)

        door_inner_y = inward_dir > 0 ? d_bounds.max.y : d_bounds.min.y
        cup_y = door_inner_y

        # Tâm cối bản lề cách mép viền cánh 21mm
        cup_x = is_left_hinge ? (door_edge_x + 21.mm) : (door_edge_x - 21.mm)
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
        
        safe_z_points = []
        door_max_z = d_bounds.max.z
        
        z_points.each do |z|
          current_z = z
          collision_detected = true
          
          while collision_detected
            collision_detected = false
            
            # 1. Quét va chạm đợt ngang
            blocked_zones.each do |zone|
              if current_z > zone[:min_z] && current_z < zone[:max_z]
                collision_detected = true
                break
              end
            end
            
            # 2. Quét va chạm ốc vít bản lề đối diện (Staggered Hinges)
            if !collision_detected && panel_hinge_registry[v_panel]
              panel_hinge_registry[v_panel].each do |existing_z|
                if (current_z - existing_z).abs < 20.mm
                  collision_detected = true
                  break
                end
              end
            end
            
            if collision_detected
              new_z = current_z + 32.mm
              if new_z > door_max_z - 50.mm
                puts "Warning: Bản lề tịnh tiến vượt quá đỉnh cánh tủ (Z=#{new_z.to_mm}mm). Hủy tịnh tiến."
                collision_detected = false # Force exit
                break
              else
                current_z = new_z
              end
            end
          end
          
          # Đăng ký Z vào lịch sử của vách
          panel_hinge_registry[v_panel] ||= []
          panel_hinge_registry[v_panel] << current_z
          safe_z_points << current_z
        end
        
        cup_z_vec = Geom::Vector3d.new(0, -inward_dir, 0)
        cup_y_vec = Geom::Vector3d.new(0, 0, 1)
        cup_x_vec = cup_y_vec * cup_z_vec

        plate_z_vec = is_left_hinge ? Geom::Vector3d.new(-1, 0, 0) : Geom::Vector3d.new(1, 0, 0)
        plate_y_vec = Geom::Vector3d.new(0, 0, 1)
        plate_x_vec = plate_y_vec * plate_z_vec

        safe_z_points.each do |hz|
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
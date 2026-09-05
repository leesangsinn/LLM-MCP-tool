def cleanup_old_hardware_minifix(ents)
  ents.to_a.each do |e|
    if e.is_a?(Sketchup::ComponentInstance) || e.is_a?(Sketchup::Group)
      inst_name = e.respond_to?(:name) ? e.name : ""
      def_name = e.respond_to?(:definition) ? e.definition.name : ""
      
      is_abf = inst_name.start_with?("_ABF_minifix") || def_name.start_with?("_ABF_minifix") || 
               inst_name.start_with?("_ABF_shelfSupport") || def_name.start_with?("_ABF_shelfSupport")
               
      if is_abf
        e.erase!
      else
        target = e.respond_to?(:definition) ? e.definition.entities : e.entities
        cleanup_old_hardware_minifix(target)
      end
    end
  end
end

def get_or_create_cam_template(model, draw_cam)
  if draw_cam
    def_name = "_ABF_minifixPlasticBase"
  else
    def_name = "_ABF_shelfSupport_D5"
  end
  
  d = model.definitions[def_name]
  d = model.definitions.add(def_name) if d.nil?
  d.entities.clear!
  
  if draw_cam
    # 1. Lỗ chốt đâm vách (Pin D5)
    d.entities.add_circle(Geom::Point3d.new(0, 8.5.mm, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
    # 2. Lỗ Cam 15mm (Nếu type là minifix)
    d.entities.add_circle(Geom::Point3d.new(0, 0, -34.mm), Geom::Vector3d.new(0, 1, 0), 7.5.mm)
  else
    # Nếu là Chốt đợt (Shelf pin)
    # Chỉ vẽ 1 vòng tròn 5mm ngay tại gốc tọa độ, mặt phẳng XY (Z=0)
    d.entities.add_circle(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(0, 0, 1), 2.5.mm)
  end
  d
end

begin
  model = Sketchup.active_model
  entities = model.entities
  
  minifix_distance = {{minifix_distance}}.mm
  face_z_idx = {{face_z_idx}}
  cam_y_dir = {{cam_y_dir}}
  draw_cam = {{draw_cam}}

  model.start_operation('Auto Insert Minifix', true)
  
  active_ents = model.active_entities
  edit_tr_inv = model.edit_transform.inverse

  cleanup_old_hardware_minifix(active_ents)

  templates = {}
  templates[:cam] = get_or_create_cam_template(model, draw_cam)

  hw_group = active_ents.add_group
  hw_group.name = draw_cam ? "Phu_Kien_Cam_Chot" : "Phu_Kien_Chot_Dot"

  groups_and_comps = active_ents.grep(Sketchup::Group) + active_ents.grep(Sketchup::ComponentInstance)
  shelves, vertical_panels = [], []

  groups_and_comps.each do |ent|
    bounds = ent.bounds
    dx, dy, dz = bounds.width.to_mm, bounds.height.to_mm, bounds.depth.to_mm
    
    if dz > 16 && dz < 19
      ent.make_unique if ent.respond_to?(:make_unique)
      shelves << ent
    elsif dx > 16 && dx < 19
      ent.make_unique if ent.respond_to?(:make_unique)
      vertical_panels << ent
    end
  end

  count = 0

  if templates[:cam]
    shelves.each do |shelf|
      vertical_panels.each do |v_panel|
        s_bounds = shelf.bounds
        v_bounds = v_panel.bounds
        
        is_left_panel = (v_bounds.center.x < s_bounds.center.x)
        
        shelf_edge_x = is_left_panel ? s_bounds.corner(0).x : s_bounds.corner(1).x
        panel_inner_x = is_left_panel ? v_bounds.corner(1).x : v_bounds.corner(0).x
        
        gap = (shelf_edge_x - panel_inner_x).abs
        
        if gap < 3.mm
          depth_y = s_bounds.depth
          start_y = s_bounds.corner(0).y
          
          cam_x = panel_inner_x
          cam_z = s_bounds.corner(face_z_idx).z
          
          y_points = [start_y + minifix_distance, start_y + depth_y - minifix_distance]
          y_points << start_y + (depth_y / 2.0) if depth_y.to_mm > 600
          
          if draw_cam
            # CAM CHỐT (Nhúng vào Đợt)
            cam_z_vec = is_left_panel ? Geom::Vector3d.new(-1, 0, 0) : Geom::Vector3d.new(1, 0, 0)
            cam_y_vec = Geom::Vector3d.new(0, 0, cam_y_dir)
            cam_x_vec = cam_y_vec * cam_z_vec

            y_points.each do |py|
              c_origin = Geom::Point3d.new(cam_x, py, cam_z)
              c_tr = Geom::Transformation.axes(c_origin, cam_x_vec, cam_y_vec, cam_z_vec)
              
              local_c_tr = edit_tr_inv * c_tr
              inst = hw_group.entities.add_instance(templates[:cam], local_c_tr)
              inst.name = "_ABF_minifixPlasticBase"
              count += 1
            end
          else
            # CHỐT ĐỢT D5 (Không nhúng vào vách nữa, thả thẳng ra ngoài)
            # Origin nằm ngay trên mặt vách.
            # Z axis của component đâm SÂU vào trong vách để ABF đục lỗ.
            pin_z_vec = is_left_panel ? Geom::Vector3d.new(-1, 0, 0) : Geom::Vector3d.new(1, 0, 0)
            pin_y_vec = Geom::Vector3d.new(0, 0, 1) # Hướng lên trên
            pin_x_vec = pin_y_vec * pin_z_vec
            
            y_points.each do |py|
              p_origin = Geom::Point3d.new(cam_x, py, s_bounds.corner(0).z)
              p_tr = Geom::Transformation.axes(p_origin, pin_x_vec, pin_y_vec, pin_z_vec)
              
              local_p_tr = edit_tr_inv * p_tr
              inst = hw_group.entities.add_instance(templates[:cam], local_p_tr)
              inst.name = "_ABF_shelfSupport_D5"
              count += 1
            end
          end
        end
      end
    end
  end

  model.commit_operation
  "Success: Auto-inserted #{count} minifix components."
rescue => e
  model.abort_operation
  "Error: #{e.message}"
end
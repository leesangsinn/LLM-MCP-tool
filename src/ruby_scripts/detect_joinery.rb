begin
  model = Sketchup.active_model
  entities = model.active_entities
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
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

begin
  model = Sketchup.active_model
  model.start_operation('Draw Basic Cabinet', true)
  ents = model.active_entities
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

  w = {{width}}.mm
  h = {{height}}.mm
  d = {{depth}}.mm
  t = {{thickness}}.mm
  bt = {{back_thickness}}.mm
  px = {{pos_x}}.mm
  py = {{pos_y}}.mm
  pz = {{pos_z}}.mm

  # Các tấm cấu tạo vỏ tủ
  draw_panel(ents, '[Vach_Trai]', t, d, h, px, py, pz)
  draw_panel(ents, '[Vach_Phai]', t, d, h, px + w - t, py, pz)
  draw_panel(ents, '[Day]', w - 2*t, d, t, px + t, py, pz)
  draw_panel(ents, '[Noc]', w - 2*t, d, t, px + t, py, pz + h - t)
  draw_panel(ents, '[Hau]', w - 2*t, bt, h - 2*t, px + t, py + d - bt, pz + t)

  model.commit_operation
  "Success: Basic cabinet {{width}}x{{height}}x{{depth}} created."
rescue => e
  model.abort_operation
  "Error: #{{e.message}}"
end
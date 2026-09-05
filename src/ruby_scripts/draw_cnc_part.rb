begin
  model = Sketchup.active_model
  model.start_operation('Draw CNC Part: {{part_name}}', true)
ents = model.active_entities

  # Vẽ tại gốc tọa độ
  group = ents.add_group
  pt1 = Geom::Point3d.new(0, 0, 0)
  pt2 = Geom::Point3d.new({{width}}.mm, 0, 0)
  pt3 = Geom::Point3d.new({{width}}.mm, {{depth}}.mm, 0)
  pt4 = Geom::Point3d.new(0, {{depth}}.mm, 0)
  
  face = group.entities.add_face(pt1, pt2, pt3, pt4)
  face.pushpull(-{{thickness}}.mm) # Extrude (SketchUp mặc định kéo âm sẽ dựng hình lên trên chuẩn Normal)

  # Đóng gói và đặt tên
  instance = group.to_component
  instance.definition.name = '{part_name}'

  # Dời đến tọa độ đích
  tr = Geom::Transformation.translation(Geom::Vector3d.new({{pos_x}}.mm, {{pos_y}}.mm, {{pos_z}}.mm))
  instance.transform!(tr)

  model.commit_operation
  "Success: Part '{part_name}' created."
rescue => e
  model.abort_operation
  "Error: #{{e.message}}"
end
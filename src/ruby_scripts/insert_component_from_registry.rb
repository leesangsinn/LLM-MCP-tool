begin
  model = Sketchup.active_model
  model.start_operation("Insert Component Registry", true)

  component_id = "{{component_id}}"
  px = {{pos_x}}.to_f
  py = {{pos_y}}.to_f
  pz = {{pos_z}}.to_f
  w = {{target_width}}.to_f
  h = {{target_height}}.to_f
  d = {{target_depth}}.to_f
  color_hex = "{{color_hex}}"
  
  registry = {
    "hoc_keo" => "C:/Users/dinhq/Downloads/THU VIEN DC 17.5mm/HocKeo.skp",
    "mat_ngan_keo" => "C:/Users/dinhq/Downloads/THU VIEN DC 17.5mm/16- Mat NK.skp"
  }
  
  path = registry[component_id]
  raise "Component ID '#{component_id}' không tồn tại trong Registry!" unless path
  
  def_name = File.basename(path, ".*")
  comp_def = model.definitions[def_name]
  unless comp_def
    if File.exist?(path)
      comp_def = model.definitions.load(path)
    else
      raise "Không tìm thấy file tại #{path}"
    end
  end
  
  tr = Geom::Transformation.translation(Geom::Vector3d.new(px.mm, py.mm, pz.mm))
  instance = model.active_entities.add_instance(comp_def, tr)
  
  # Bơm lọt lòng thô cho DC tự trừ hao. 
  # Tính toán theo mm như yêu cầu
  instance.set_attribute('dynamic_attributes', 'lenx', w)
  instance.set_attribute('dynamic_attributes', 'leny', d)
  instance.set_attribute('dynamic_attributes', 'lenz', h)
  
  # Kích hoạt Redraw
  if defined?($dc_observers)
    $dc_observers.get_latest_class.redraw_with_undo(instance)
  end

  model.commit_operation
  "Thành công: Đã chèn #{component_id} tại tọa độ (#{px}, #{py}, #{pz})"
rescue => e
  model.abort_operation
  "Error: #{e.message}\n#{e.backtrace.join("\n")}"
end

require 'json'

begin
  model = Sketchup.active_model
  model.start_operation("Draw Smart Cabinet", true)

  # 1. Khởi tạo/Kiểm tra Material MDF_17_MM (ABF Standard)
  materials = model.materials
  mdf_mat = materials["MDF_17_MM"]
  unless mdf_mat
    mdf_mat = materials.add("MDF_17_MM")
    mdf_mat.color = Sketchup::Color.new(245, 245, 220) # Màu be nhẹ
  end

  parts_json_str = %q({{parts_json}})
  parts = JSON.parse(parts_json_str)

  parts.each do |part|
    type = part["type"]
    name = part["name"]
    w_mm = part["w"].to_f
    d_mm = part["d"].to_f
    h_mm = part["h"].to_f
    x = part["x"].to_f.mm
    y = part["y"].to_f.mm
    z = part["z"].to_f.mm
    mat_name = part["material"]

    if type == "panel"
      # Vẽ ván bằng raw geometry
      group = model.active_entities.add_group
      
      pt1 = [0, 0, 0]
      pt2 = [w_mm.mm, 0, 0]
      pt3 = [w_mm.mm, d_mm.mm, 0]
      pt4 = [0, d_mm.mm, 0]
      
      face = group.entities.add_face(pt1, pt2, pt3, pt4)
      # pushpull: do vẽ tại Z=0, nên ta pushpull lên. 
      # Mặc định face sinh ra có normal hướng xuống. Pushpull số âm sẽ kéo lên.
      face.pushpull(-h_mm.mm) 
      
      # Tạo Component
      comp_def = group.to_component
      comp_def.name = name
      comp_inst = comp_def.instances.first
      
      # Gán vật liệu
      comp_inst.material = mdf_mat
      
      # Dời về đúng tọa độ X, Y, Z
      t = Geom::Transformation.translation(Geom::Vector3d.new(x, y, z))
      comp_inst.transform!(t)
      
    elsif type == "drawer"
      # Chèn hộc kéo
      comp_def = model.definitions["Hoc_Keo"]
      unless comp_def
        # Load từ file
        path = "C:/Users/dinhq/Downloads/THU VIEN DC 17.5mm/HocKeo.skp"
        if File.exist?(path)
          comp_def = model.definitions.load(path)
        else
          raise "Không tìm thấy thư viện HocKeo.skp tại #{path}"
        end
      end
      
      t = Geom::Transformation.translation(Geom::Vector3d.new(x, y, z))
      comp_inst = model.active_entities.add_instance(comp_def, t)
      
      # Truyền Dynamic Attributes (Tùy thuộc vào cấu trúc của HocKeo.skp)
      comp_inst.set_attribute("dynamic_attributes", "lenx", w_mm.to_f)
      comp_inst.set_attribute("dynamic_attributes", "leny", d_mm.to_f)
      comp_inst.set_attribute("dynamic_attributes", "lenz", h_mm.to_f)
      $dc_observers.get_latest_class.redraw_with_undo(comp_inst) if defined?($dc_observers)
      
      # Gán vật liệu
      comp_inst.material = mdf_mat
    end
  end

  model.commit_operation
  "Thành công! Đã vẽ xong tủ."
rescue => e
  model.abort_operation
  "Error: #{e.message}\n#{e.backtrace.join("\n")}"
end

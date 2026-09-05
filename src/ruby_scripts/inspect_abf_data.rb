require 'json'
begin
  model = Sketchup.active_model
  sel = model.selection
  
  # Tìm đối tượng mục tiêu: Lấy đối tượng đang chọn, nếu không có thì lấy 1 ComponentInstance bất kỳ
  target = sel.first
  target = model.entities.grep(Sketchup::ComponentInstance).first if target.nil?
  
  attributes = {}
  if target && target.attribute_dictionaries
    target.attribute_dictionaries.each do |dict|
      dict_name = dict.name
      attributes[dict_name] = {}
      dict.each_pair do |key, value|
        # Ép kiểu value về string để tránh lỗi serialize JSON với các đối tượng SketchUp đặc thù
        attributes[dict_name][key] = value.to_s
      end
    end
  end
  
  # Quét bộ nhớ Ruby xem có những Module/Class nào của ABF đang chạy ngầm
  abf_modules = Object.constants.select { |c| c.to_s.upcase.include?("ABF") }.map { |c| c.to_s }
  
  result = {
    "target_name" => target ? (target.respond_to?(:name) && !target.name.empty? ? target.name : target.definition.name) : "No target found",
    "attributes" => attributes,
    "abf_modules_in_memory" => abf_modules
  }
  
  result.to_json
rescue => e
  { "error" => e.message, "backtrace" => e.backtrace }.to_json
end
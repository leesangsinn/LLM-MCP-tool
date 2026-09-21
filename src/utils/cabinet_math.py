import math

class CabinetCalculator:
    def __init__(self, layout_data):
        self.layout = layout_data
        self.dims = self.layout.get("total_dimensions", {})
        self.width = self.dims.get("width", 1000)
        self.height = self.dims.get("height", 2000)
        self.depth = self.dims.get("depth", 600)
        self.door_style = self.layout.get("door_style", "overlay")
        self.back_style = self.layout.get("back_style", "grooved")
        self.columns = self.layout.get("columns", [])
        
        self.thickness = 17.0
        self.back_thickness = 6.0
        self.toe_kick_height = 80.0
        
        self.parts = []

    def snap_to_slide_length(self, clearance_depth: float) -> float:
        """Làm tròn trừ lùi về chuẩn ray trượt bi (300, 350, 400, 450, 500)"""
        standard_slides = [300, 350, 400, 450, 500]
        # Nếu nhỏ hơn 300 thì trả về 300 (hoặc lỗi), nhưng ưu tiên chặn dưới.
        valid_slides = [s for s in standard_slides if s <= clearance_depth]
        if not valid_slides:
            return 250.0 # Standard mini
        return max(valid_slides)

    def _add_part(self, name, w, d, h, x, y, z, type="panel"):
        self.parts.append({
            "name": name,
            "w": float(w),
            "d": float(d),
            "h": float(h),
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "type": type,
            "material": "MDF_17_MM"
        })

    def generate_parts(self):
        # 1. Carcass
        # Day (Bottom)
        day_z = self.toe_kick_height
        
        # Offset Y for Back Panel
        back_offset = 0
        internal_depth = self.depth
        if self.back_style == "grooved":
            # Hậu lùa rãnh 8mm cách mép sau 17mm.
            # Lọt lòng tính từ mép ván hậu đến mép trước.
            # Đơn giản hóa: Day, Noc thụt vào 17mm phía sau, ván hậu dày 6mm.
            # Hồi giữ nguyên full depth.
            day_depth = self.depth - 17.0 # Trừ 17mm mép sau để lùa hậu
            internal_depth = day_depth
            back_offset = 17.0
        else:
            # Hậu phủ (overlay) bắn phía sau. Khung tủ lọt vào trong.
            day_depth = self.depth - self.back_thickness
            internal_depth = day_depth
            back_offset = self.back_thickness
            
        # Noc (Top)
        noc_z = self.height - self.thickness
        
        # Hoi Trai, Hoi Phai (Left/Right Sides)
        self._add_part("Hoi_Trai", self.thickness, self.depth, self.height, 0, 0, 0)
        self._add_part("Hoi_Phai", self.thickness, self.depth, self.height, self.width - self.thickness, 0, 0)
        
        # Day, Noc (nằm giữa 2 hồi)
        carcass_inner_w = self.width - (2 * self.thickness)
        self._add_part("Day", carcass_inner_w, day_depth, self.thickness, self.thickness, back_offset, day_z)
        self._add_part("Noc", carcass_inner_w, day_depth, self.thickness, self.thickness, back_offset, noc_z)
        
        # 2. Columns (Dividers) & Internals
        current_x = self.thickness
        for col_idx, col in enumerate(self.columns):
            ratio = col.get("width_ratio", 1.0)
            col_inner_w = (carcass_inner_w * ratio)
            
            # Divider right side of column (if not last)
            is_last = (col_idx == len(self.columns) - 1)
            if not is_last:
                col_inner_w -= self.thickness / 2.0 # chia sẻ độ dày vách chia
                div_x = current_x + col_inner_w
                div_h = noc_z - (day_z + self.thickness)
                self._add_part("Vach_Chia", self.thickness, day_depth, div_h, div_x, back_offset, day_z + self.thickness)
            
            # Internals (Drawers, Shelves, Hanging)
            internals = col.get("internal_layout", [])
            
            # Khởi tạo drawer snapping
            drawer_clearance = internal_depth
            if self.door_style == "inset":
                drawer_clearance -= self.thickness # lùi cánh lọt lòng
                
            drawer_slide = self.snap_to_slide_length(drawer_clearance - 50.0) # Trừ hao 50mm dây điện/rãnh kéo
            
            current_z = day_z + self.thickness
            auto_height = noc_z - current_z # TODO: Calculate remaining space accurately based on fixed heights
            
            for item in internals:
                item_type = item.get("type", "empty")
                item_h = item.get("height")
                count = item.get("count", 1)
                
                if item_h is None:
                    item_h = auto_height / max(count, 1) # Auto scale
                
                for i in range(count):
                    if item_type == "drawers":
                        # Component: Hoc Keo
                        # Insert at bottom-left of the slot
                        self._add_part("Hoc_Keo", col_inner_w, drawer_slide, item_h, current_x, back_offset + (internal_depth - drawer_slide) if self.door_style == "inset" else 0, current_z, type="drawer")
                        current_z += item_h
                    elif item_type == "shelves":
                        # Add a shelf at top of this height
                        current_z += item_h
                        self._add_part("Dot_Chia", col_inner_w, day_depth - 20, self.thickness, current_x, back_offset + 20, current_z - self.thickness)
                    elif item_type == "hanging_space":
                        current_z += item_h
                    elif item_type == "top_shelf":
                        current_z += item_h
                        self._add_part("Dot_Noc", col_inner_w, day_depth, self.thickness, current_x, back_offset, current_z - self.thickness)
            
            current_x += col_inner_w + self.thickness
            
        return self.parts

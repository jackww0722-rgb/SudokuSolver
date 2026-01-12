import cv2  # 需要 opencv-python
import numpy as np
from pathlib import Path
from typing import Tuple, Union

class VisualDebugger:
    """
    視覺化除錯模組：用於驗證座標系統定義
    """
    def __init__(self, image_path: Union[str, Path]):
        self.image_path = Path(image_path)
        self.image = cv2.imread(str(self.image_path))
        if self.image is None:
            raise FileNotFoundError(f"無法讀取圖片: {self.image_path}")
        self.height, self.width = self.image.shape[:2]

    def draw_debug_boxes(self, target_y_ratio: float, box_h_ratio: float = 0.1, box_w_ratio: float = 0.1) -> None:
        """
        在圖片上繪製兩種邏輯的框進行比對
        :param target_y_ratio: 數據中的 Y 值 (例如 0.4373)
        :param box_h_ratio: 預設裁切框高度比例 (例如 0.1)
        :param box_w_ratio: 預設裁切框寬度比例
        """
        # 轉換為像素
        y_val = int(self.height * target_y_ratio)
        h_px = int(self.height * box_h_ratio)
        w_px = int(self.width * box_w_ratio)
        
        # 假設 X 軸在中間方便觀察 (您可以根據實際 X 數據調整)
        x_start = int(self.width * 0.5) - (w_px // 2)

        # -------------------------------------------------
        # 1. 紅色框 (Red): 假設數值是 Top-Left (起始點)
        # -------------------------------------------------
        # 框的頂部就是 y_val
        top_left_red = (x_start, y_val)
        bottom_right_red = (x_start + w_px, y_val + h_px)
        
        cv2.rectangle(self.image, top_left_red, bottom_right_red, (0, 0, 255), 3)
        cv2.putText(self.image, "Top-Left Logic", (x_start, y_val - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # -------------------------------------------------
        # 2. 綠色框 (Green): 假設數值是 Center (中心點)
        # -------------------------------------------------
        # 框的頂部 = 中心點 - (高度的一半)
        y_top_green = y_val - (h_px // 2)
        
        top_left_green = (x_start + w_px + 20, y_top_green) # 稍微往右移一點以免重疊
        bottom_right_green = (x_start + w_px + 20 + w_px, y_top_green + h_px)
        
        cv2.rectangle(self.image, top_left_green, bottom_right_green, (0, 255, 0), 3)
        cv2.putText(self.image, "Center Logic", (x_start + w_px + 20, y_top_green - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    def save_result(self, output_name: str = "debug_output.jpg"):
        output_path = self.image_path.parent / output_name
        cv2.imwrite(str(output_path), self.image)
        print(f"診斷圖片已儲存至: {output_path}")

# --- 主程式 ---
if __name__ == "__main__":
    # 請將此處換成您手機的截圖路徑 (最好是未裁切的全螢幕截圖)
    # 如果您手邊只有裁切後的小圖，這個測試會不準，需要全圖
    img_file = Path(__file__).resolve().parent / "screenshot_full.png"

    
    # 您的數據
    Target_Y = 0.4373 

    try:
        if img_file.exists():
            debugger = VisualDebugger(img_file)
            # 假設框的大小約佔畫面的 10% (您可以依實際調整)
            debugger.draw_debug_boxes(target_y_ratio=Target_Y, box_h_ratio=0.1)
            debugger.save_result()
        else:
            print(f"請準備一張全螢幕截圖並命名為 {img_file}")
    except Exception as e:
        print(f"發生錯誤: {e}")
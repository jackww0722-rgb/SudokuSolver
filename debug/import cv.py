import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict

class ImagePipelineTracer:
    """
    影像處理歷程追蹤器
    用於偵測在 Resize, Padding 或 Crop 過程中，座標系統是否發生了偏移
    """
    def __init__(self, original_image_path: Path):
        self.path = original_image_path
        self.history: List[Dict] = []
        
        # 讀取原始圖片
        if not self.path.exists():
            raise FileNotFoundError(f"找不到檔案: {self.path}")
            
        self.original_img = cv2.imread(str(self.path))
        self.current_h, self.current_w = self.original_img.shape[:2]
        
        # 記錄初始狀態
        self._log_step("原始讀取", self.current_h, self.current_w, offset_y=0)

    def _log_step(self, stage_name: str, h: int, w: int, offset_y: int = 0):
        print(f"[{stage_name}] 尺寸: {w}x{h} | Y軸偏移累積: {offset_y} px")
        self.history.append({
            "stage": stage_name,
            "width": w,
            "height": h,
            "offset_y": offset_y
        })

    def simulate_processing_check(self, target_y_ratio: float = 0.4373):
        """
        模擬常見的錯誤處理流程，幫您找出偏移原因
        """
        print(f"\n--- 開始診斷座標偏移 (目標比例: {target_y_ratio}) ---")
        
        # 1. 原始計算位置
        original_y = int(self.current_h * target_y_ratio)
        print(f"1. 原始預期 Y 座標 (絕對值): {original_y} px")

        # 2. 模擬情境 A：被誤切的 ROI (例如切掉了上方的狀態列 60px)
        # 許多自動化程式會先切掉 status bar 再處理
        status_bar_height = 80 
        print(f"\n[模擬情境 A] 程式偷偷切掉了上方 Status Bar ({status_bar_height}px)...")
        
        # 如果程式切掉上面，但您仍用原圖比例算，座標會對不上
        roi_h = self.current_h - status_bar_height
        recalc_y = int(roi_h * target_y_ratio)
        diff = original_y - (recalc_y + status_bar_height)
        print(f"   -> 若發生此處理，實際落點誤差: {diff} px")

        # 3. 模擬情境 B：模型輸入 Resize (例如 YOLO 常用的 640x640 補黑邊)
        target_size = 640
        scale = min(target_size / self.current_h, target_size / self.current_w)
        new_h, new_w = int(self.current_h * scale), int(self.current_w * scale)
        
        # 計算 Padding (補黑邊)
        pad_y = (target_size - new_h) // 2
        
        print(f"\n[模擬情境 B] 縮放並補黑邊 (Letterbox) 至 {target_size}x{target_size}...")
        print(f"   -> 縮放後高度: {new_h}, 上下補黑邊: {pad_y} px")
        
        # 逆推座標
        # 如果您的 0.4373 是在「原始圖」算的，但在「縮放圖」上用...
        scaled_y_on_canvas = (original_y * scale) + pad_y
        
        # 轉回原始比例看誤差
        restored_y = (scaled_y_on_canvas - pad_y) / scale
        print(f"   -> 座標轉換檢查: {original_y} -> {restored_y:.2f} (若有誤差代表數學轉換正確)")
        print(f"   -> **關鍵提示**: 如果您在縮放後的圖上直接畫框，Y 座標會包含 {pad_y}px 的黑邊偏移量！")

    def analyze_image_composition(self):
        """簡單分析圖片是否包含上下黑邊或異常區域"""
        gray = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2GRAY)
        
        # 檢查頂部 5% 是否全黑或全白 (可能是 Status Bar 造成的干擾)
        top_slice = gray[0:int(self.current_h*0.05), :]
        if np.mean(top_slice) < 10 or np.mean(top_slice) > 245:
             print("\n[警告] 圖片頂部似乎包含純色區域 (狀態列/黑邊)。")
             print("這會導致 Y 軸起始點 (0,0) 與遊戲畫面實際起始點不同。")

# --- 主程式 ---
if __name__ == "__main__":
    # 使用您上傳的這張處理過的圖來分析
    # 請確保這張圖在程式碼旁邊
    img_path = Path(__file__).resolve().parent / "debug_output.jpg"
    # 組合出絕對路徑

    
    try:
        tracer = ImagePipelineTracer(img_path)
        tracer.analyze_image_composition()
        tracer.simulate_processing_check(target_y_ratio=0.4373)
    except Exception as e:
        print(f"執行失敗: {e}")
        print("請確認 'debug_output.jpg' 是否存在於資料夾中。")
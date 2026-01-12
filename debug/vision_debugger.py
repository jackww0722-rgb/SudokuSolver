import cv2
import numpy as np
from pathlib import Path

class VisionDebugger:
    """
    影像視覺除錯模組
    專注於解決：座標正確但無法辨識數字/線條的問題
    """
    def __init__(self, output_dir: str = "debug_vision"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_and_show(self, image_path: Path):
        """
        讀取圖片並展示電腦「真正看到」的畫面 (二值化結果)
        """
        # 1. 讀取圖片 (處理 Windows 中文路徑問題)
        img_array = np.fromfile(str(image_path), dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            print("❌ 讀取失敗，請確認路徑。")
            return

        # 2. 轉為灰階
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 3. 嘗試三種不同的處理手法，讓您比較哪一種最清楚
        
        # 方法 A: 固定閾值 (適合光線均勻的畫面)
        # 127 是中間值，大於127變白，小於變黑
        _, thresh_fixed = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # 方法 B: 自適應閾值 (Adaptive Threshold) - 適合有陰影或漸層的畫面
        # 這通常是數獨解題最強的方法
        thresh_adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # 方法 C: 降噪後處理 (先模糊再二值化，去除雜訊)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh_blur = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # 4. 顯示結果並存檔
        print(f"👀 正在顯示除錯視窗... (按任意鍵切換/關閉)")
        
        # 顯示原圖
        self._show_window("1. Original (Color)", img)
        
        # 顯示方法 A
        self._show_window("2. Fixed Threshold (Simple)", thresh_fixed)
        cv2.imwrite(str(self.output_dir / "method_a_fixed.png"), thresh_fixed)

        # 顯示方法 B (推薦)
        self._show_window("3. Adaptive Threshold (Standard)", thresh_adaptive)
        cv2.imwrite(str(self.output_dir / "method_b_adaptive.png"), thresh_adaptive)

        # 顯示方法 C
        self._show_window("4. Blurred + Adaptive (Cleanest)", thresh_blur)
        cv2.imwrite(str(self.output_dir / "method_c_blur.png"), thresh_blur)

        print(f"✅ 處理後的圖片已儲存至: {self.output_dir}")

    def _show_window(self, title, img):
        """輔助函式：顯示縮放後的圖片以免螢幕塞不下"""
        h, w = img.shape[:2]
        scale = 0.4  # 縮小顯示比例
        resized = cv2.resize(img, (int(w * scale), int(h * scale)))
        cv2.imshow(title, resized)
        cv2.waitKey(0) # 等待按鍵
        cv2.destroyWindow(title)

# --- Usage ---
if __name__ == "__main__":
    # 請將這裡換成您「目前截圖下來的那張圖片」的路徑
    # 或是您上次存的 debug_screen.png
    target_image = Path(__file__).parent.resolve() / "debug_screen.png"
    
    if target_image.exists():
        debugger = VisionDebugger()
        debugger.process_and_show(target_image)
    else:
        print(f"❌ 找不到圖片: {target_image}，請先截一張圖。")
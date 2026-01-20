import tkinter as tk
from tkinter import messagebox
from tkinter import ttk  # 引入現代化元件庫
import threading
import time
from ctypes import windll # 用來處理 Windows 解析度問題

# 引入您的大腦 (假設路徑正確)
from core import bot

class SudokuBotGUI:
    def __init__(self, root):
        self.root = root
        
        # --- 1. 解決模糊與字體過小問題 (關鍵) ---
        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass # 非 Windows 系統或舊版 Windows 略過

        # --- 2. 視窗設定 ---
        self.root.title("數獨自動化助手")
        # 移除固定大小，改用 minsize，讓內容撐開
        # self.root.geometry("350x300") 
        self.root.resizable(False, False)
        
        # 設定風格
        self.style = ttk.Style()
        self.style.theme_use('vista') # Windows 原生風格
        
        # 設定全域字體 (解決字體怪怪的問題)
        default_font = ("微軟正黑體", 10)
        self.style.configure('.', font=default_font)
        self.style.configure('TButton', font=default_font, padding=5)
        self.style.configure('Header.TLabel', font=("微軟正黑體", 14, "bold"), foreground="#2c3e50")
        self.style.configure('Status.TLabel', font=("微軟正黑體", 11, "bold"), foreground="#2980b9")

        # 初始化 Bot
        self.bot = bot.SudokuBot()
        self.is_running = False 

        # --- 3. 介面佈局 (使用 Frame 增加內縮) ---
        main_frame = ttk.Frame(root, padding="20 20 20 20")
        main_frame.pack(fill='both', expand=True)

        # 1. 標題區
        self.label_title = ttk.Label(main_frame, text="Sudoku Bot Controller", style="Header.TLabel")
        self.label_title.pack(pady=(0, 5))

        self.label_status = ttk.Label(main_frame, text="準備就緒 - 等待指令", style="Status.TLabel")
        self.label_status.pack(pady=(0, 15))

        # 分隔線
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)

        # 2. 快速按鈕區 (執行 10 次)
        # 注意: ttk.Button 不支援直接設定 bg 顏色，但外觀會比較現代
        self.btn_run_10 = ttk.Button(main_frame, text="🔥 直接執行 10 次", 
                                     command=lambda: self.start_thread(10))
        self.btn_run_10.pack(fill='x', pady=5)

        # 3. 自訂次數區 (使用 LabelFrame 包起來比較好看)
        custom_group = ttk.LabelFrame(main_frame, text="自訂任務", padding="10")
        custom_group.pack(fill='x', pady=10)

        ttk.Label(custom_group, text="執行次數:").pack(side="left")
        
        self.entry_count = ttk.Entry(custom_group, width=8, justify='center')
        self.entry_count.insert(0, "1")
        self.entry_count.pack(side="left", padx=10)

        self.btn_run_custom = ttk.Button(custom_group, text="▶ 開始", 
                                         command=self.on_click_custom_run)
        self.btn_run_custom.pack(side="left", fill='x', expand=True)

        # 4. 底部資訊
        self.lbl_info = ttk.Label(main_frame, text="※ 執行期間請勿移動滑鼠鍵盤", 
                                  font=("微軟正黑體", 8), foreground="gray")
        self.lbl_info.pack(side="bottom", pady=(10, 0))

    # --- 以下邏輯完全沒變，只有改 config 的部分配合 ttk ---

    def on_click_custom_run(self):
        try:
            count = int(self.entry_count.get())
            if count <= 0: raise ValueError
            self.start_thread(count)
        except ValueError:
            messagebox.showerror("錯誤", "請輸入正確的數字！")

    def start_thread(self, count):
        if self.is_running:
            messagebox.showwarning("警告", "機器人正在執行中...")
            return

        self.is_running = True
        self.btn_run_10.state(["disabled"])      # ttk 的寫法不同
        self.btn_run_custom.state(["disabled"])  # ttk 的寫法不同
        
        task_thread = threading.Thread(target=self.run_logic, args=(count,))
        task_thread.daemon = True 
        task_thread.start()

    def run_logic(self, total_rounds):
        try:
            for i in range(total_rounds):
                current_round = i + 1
                # ttkLabel 修改顏色需要用 style，這裡簡單處理直接改 text
                # 如果要改顏色，建議用 style.configure 或維持現狀
                self.label_status.config(text=f"🔄 執行中: {current_round} / {total_rounds}")
                
                print(f"\n=== GUI: 第 {current_round} 局開始 ===")
                self.bot.run_round_with_retry(current_round=i, total_rounds=total_rounds)

                if i < total_rounds - 1:
                    self.label_status.config(text=f"⏳ 休息中...")

            self.label_status.config(text="✅ 任務完成！")
            
        except Exception as e:
            print(f"❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()
            self.label_status.config(text="❌ 發生錯誤")
            messagebox.showerror("錯誤", f"發生異常：\n{e}")

        finally:
            self.reset_ui_state()

    def reset_ui_state(self):
        self.is_running = False
        try:
            # ttk 的 state 恢復寫法
            self.btn_run_10.state(["!disabled"]) 
            self.btn_run_custom.state(["!disabled"])
        except:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    # 讓視窗置中 (選用)
    window_width = 320
    window_height = 350
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

    app = SudokuBotGUI(root)
    root.mainloop()
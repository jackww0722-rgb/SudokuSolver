import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
import time
from ctypes import windll

# 引入核心
from core import bot

class SudokuBotGUI:
    def __init__(self, root):
        self.root = root
        
        # 1. DPI 設定
        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        # 2. 視窗設定
        self.root.title("數獨自動化助手")
        self.root.geometry("360x320")
        self.root.resizable(False, False)
        
        self.style = ttk.Style()
        self.style.theme_use('vista')
        self.style.configure('.', font=("微軟正黑體", 10))
        self.style.configure('Status.TLabel', font=("微軟正黑體", 11, "bold"))

        # --- 關鍵修改：一開始不要實例化 Bot ---
        self.bot = None 
        self.is_running = False

        # --- 介面佈局 ---
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill='both', expand=True)

        # 標題
        ttk.Label(main_frame, text="Sudoku Bot Controller", font=("微軟正黑體", 14, "bold")).pack(pady=(0, 10))

        # 狀態顯示區
        self.label_status = ttk.Label(main_frame, text="⏳ 正在搜尋裝置...", style="Status.TLabel", foreground="orange")
        self.label_status.pack(pady=(0, 15))

        # 重連按鈕 (預設隱藏，失敗時才出現)
        self.btn_reconnect = ttk.Button(main_frame, text="🔄 重試連線", command=self.start_connect_thread)
        # 先不要 pack，等失敗再顯示

        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)

        # 控制區 (預設全部 disabled，等到連線成功才打開)
        self.btn_run_10 = ttk.Button(main_frame, text="🔥 直接執行 10 次", state="disabled",
                                     command=lambda: self.start_task_thread(10))
        self.btn_run_10.pack(fill='x', pady=5)

        custom_group = ttk.LabelFrame(main_frame, text="自訂任務", padding="10")
        custom_group.pack(fill='x', pady=10)

        ttk.Label(custom_group, text="次數:").pack(side="left")
        self.entry_count = ttk.Entry(custom_group, width=8, justify='center')
        self.entry_count.insert(0, "1")
        self.entry_count.pack(side="left", padx=10)

        self.btn_run_custom = ttk.Button(custom_group, text="▶ 開始", state="disabled",
                                         command=self.on_click_custom_run)
        self.btn_run_custom.pack(side="left", fill='x', expand=True)

        # 底部資訊
        self.lbl_info = ttk.Label(main_frame, text="請確保模擬器已開啟且 ADB 正常", foreground="gray", font=("微軟正黑體", 8))
        self.lbl_info.pack(side="bottom")

        # --- 視窗啟動後，自動開始連線 ---
        # 延遲 500ms 後執行，讓視窗先渲染出來
        self.root.after(500, self.start_connect_thread)

    # ==========================================
    # 🔌 連線邏輯 (新增部分)
    # ==========================================
    def start_connect_thread(self):
        """ 啟動背景連線 """
        # 隱藏重試按鈕，更新狀態
        self.btn_reconnect.pack_forget()
        self.label_status.config(text="⏳ 正在連線中...", foreground="orange")
        self.btn_run_10.state(["disabled"])
        self.btn_run_custom.state(["disabled"])

        # 開執行緒去連線
        threading.Thread(target=self._connect_task, daemon=True).start()

    def _connect_task(self):
        """ 真正的連線動作 (在背景執行) """
        try:
            # 嘗試建立 Bot (這會觸發 AdbController 的 init)
            # 如果沒抓到裝置，這裡應該要報錯
            self.bot = bot.SudokuBot()
            
            # 連線成功 -> 更新 UI
            self.root.after(0, self._on_connect_success)
        except Exception as e:
            print(f"連線失敗: {e}")
            # 連線失敗 -> 更新 UI
            self.root.after(0, lambda: self._on_connect_fail(str(e)))

    def _on_connect_success(self):
        """ 連線成功後的 UI 更新 """
        self.label_status.config(text="✅ 裝置已連線 (準備就緒)", foreground="green")
        self.btn_run_10.state(["!disabled"])
        self.btn_run_custom.state(["!disabled"])
        self.lbl_info.config(text=f"解析度: {self.bot.adb.real_w}x{self.bot.adb.real_h}")

    def _on_connect_fail(self, error_msg):
        """ 連線失敗後的 UI 更新 """
        self.label_status.config(text="❌ 未偵測到裝置", foreground="red")
        # 顯示重試按鈕
        self.btn_reconnect.pack(after=self.label_status, pady=5)
        messagebox.showerror("連線錯誤", f"無法連接到 ADB 裝置。\n請檢查模擬器是否開啟。\n\n錯誤訊息: {error_msg}")

    # ==========================================
    # 🎮 任務執行邏輯 (原本的部分)
    # ==========================================
    def on_click_custom_run(self):
        try:
            count = int(self.entry_count.get())
            if count <= 0: raise ValueError
            self.start_task_thread(count)
        except ValueError:
            messagebox.showerror("錯誤", "請輸入正確的數字！")

    def start_task_thread(self, count):
        if self.bot is None:
            messagebox.showerror("錯誤", "尚未連線到機器人！")
            return

        if self.is_running:
            return

        self.is_running = True
        self.btn_run_10.state(["disabled"])
        self.btn_run_custom.state(["disabled"])
        self.btn_reconnect.state(["disabled"]) # 執行中也不准按重連
        
        threading.Thread(target=self.run_logic, args=(count,), daemon=True).start()

    def run_logic(self, total_rounds):
        try:
            for i in range(total_rounds):
                # 這裡要加一個檢查，怕跑到一半視窗關了或斷線
                if self.bot is None: break

                current = i + 1
                self.label_status.config(text=f"🔄 執行中: {current} / {total_rounds}", foreground="blue")
                
                # 呼叫 Bot 執行
                self.bot.run_round_with_retry() # 或是 run_round_with_retry

                if i < total_rounds - 1:
                    self.label_status.config(text="⏳ 休息中...")
                    time.sleep(1)

            self.label_status.config(text="✅ 任務完成！", foreground="green")
            
        except Exception as e:
            print(f"執行錯誤: {e}")
            self.label_status.config(text="❌ 執行發生錯誤", foreground="red")
        finally:
            self.reset_ui_state()

    def reset_ui_state(self):
        self.is_running = False
        try:
            self.btn_run_10.state(["!disabled"])
            self.btn_run_custom.state(["!disabled"])
            if self.btn_reconnect.winfo_ismapped(): # 如果重連按鈕有顯示，也要啟用
                 self.btn_reconnect.state(["!disabled"])
        except:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    # 視窗置中設定
    window_width, window_height = 360, 350
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int((screen_width/2) - (window_width/2))
    y = int((screen_height/2) - (window_height/2))
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    app = SudokuBotGUI(root)
    root.mainloop()
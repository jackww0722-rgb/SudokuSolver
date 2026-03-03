import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
import time
from ctypes import windll
from core.action import StopTaskException

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
        self.root.geometry("360x350")
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

        # 🆕 新增：暫停/繼續 按鈕
        # ==========================================
        # 預設是 disabled (因為還沒開始跑)，放在「自訂任務」下面
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=5)

        self.btn_pause = ttk.Button(control_frame, text="⏸️ 暫停", state="disabled",
                                    command=self.on_click_pause)
        self.btn_pause.pack(side="left", fill='x', expand=True, padx=(0, 2))

        # ==========================================
        # 🆕 新增：停止按鈕
        # ==========================================
        self.btn_stop = ttk.Button(control_frame, text="⏹️ 停止", state="disabled",
                                   command=self.on_click_stop)
        self.btn_stop.pack(side="left", fill='x', expand=True, padx=(2, 0))

        custom_group = ttk.LabelFrame(main_frame, text="自訂任務", padding="10")
        custom_group.pack(fill='x', pady=10)

        ttk.Label(custom_group, text="次數:").pack(side="left")
        self.entry_count = ttk.Entry(custom_group, width=8, justify='center')
        self.entry_count.insert(0, "1")
        self.entry_count.pack(side="left", padx=10)

        self.btn_run_custom = ttk.Button(custom_group, text="開始", state="disabled",
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
        if self.bot:
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

    def on_click_pause(self):
        """ 切換 暫停/繼續 狀態 """
        if not self.bot: return

        if self.bot.pause_event.is_set():
            # 🟢 綠燈 -> 🔴 紅燈 (執行 -> 暫停)
            self.bot.pause_event.clear()
            self.btn_pause.config(text="繼續執行")
            self.label_status.config(text="已暫停 (等待指令)", foreground="orange")
        else:
            # 🔴 紅燈 -> 🟢 綠燈 (暫停 -> 執行)
            self.bot.pause_event.set()
            self.btn_pause.config(text="暫停")
            self.label_status.config(text="恢復執行中...", foreground="blue")

    def on_click_stop(self):
        """ 按下停止鍵的處理邏輯 """
        if not self.bot: return
        
        # 1. 鎖住按鈕，避免連點
        self.btn_stop.config(state="disabled")
        self.btn_pause.config(state="disabled")
        self.label_status.config(text="🛑 正在停止中，請稍候...", foreground="red")
        
        # 2. 觸發停止訊號
        self.bot.stop_event.set()

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
        # ==========================================
        # 🔓 啟用暫停/停止按鈕
        # ==========================================
        self.bot.stop_event.clear()  # 取消停止狀態
        self.bot.pause_event.set() # 確保一定是綠燈開始
        self.btn_pause.config(text="⏸️ 暫停", state="!disabled") # 啟用按鈕
        self.btn_stop.config(state="!disabled")
        
        threading.Thread(target=self.run_logic, args=(count,), daemon=True).start()

    def run_logic(self, total_rounds):
        # 建議加個統計變數，更有成就感
        success_count = 0
        fail_count = 0

        try:
            for i in range(total_rounds):
                # 1. 安全檢查
                if self.bot is None: break
                if not self.is_running: break # 如果被按下停止鍵

                current = i + 1
                
                # 更新 UI
                self.label_status.config(
                    text=f"🔄 執行中: {current}/{total_rounds} (成功:{success_count} 失敗:{fail_count})", 
                    foreground="blue"
                )
                
                # ==========================================
                # 2. 呼叫 Bot 並接收回傳值 (True/False)
                # ==========================================
                # 這裡不會再報錯了，而是回傳 True 或 False
                is_success = self.bot.run_round_with_retry(
                    current_round=current, 
                    total_rounds=total_rounds
                )

                # ==========================================
                # 3. 根據結果處理 UI
                # ==========================================
                if is_success:
                    success_count += 1
                    print(f"✅ 第 {current} 局執行成功")
                else:
                    fail_count += 1
                    # 因為 Bot 內部已經做過「異常恢復」了
                    # 所以這裡只要記錄失敗，然後讓迴圈「繼續」跑下一局即可
                    print(f"⚠️ 第 {current} 局執行失敗 (已嘗試救援)")
                    self.label_status.config(text=f"⚠️ 本局失敗，準備下一局...", foreground="orange")
                    
                    # 失敗後通常建議多休息一下，讓系統緩衝
                    time.sleep(2) 

                # 4. 回合間的休息
                if i < total_rounds - 1:
                    self.label_status.config(text="⏳ 休息中...")
                    time.sleep(1)

            # 迴圈結束
            final_msg = f"✅ 任務結束！成功: {success_count}, 失敗: {fail_count}"
            self.label_status.config(text=final_msg, foreground="green" if fail_count == 0 else "orange")

        except StopTaskException as e:
            print(f"🛑 {e}")
            self.label_status.config(text=f"🛑 任務已手動中止 (已完成: {success_count})", foreground="red")
            
        except Exception as e:
            # 這裡只會捕捉「程式碼錯誤」或「連線中斷」等嚴重錯誤
            print(f"❌ 系統發生嚴重錯誤: {e}")
            import traceback
            traceback.print_exc() # 印出詳細錯誤，方便您除錯
            self.label_status.config(text="❌ 系統錯誤 (請看終端機)", foreground="red")
        
        finally:
            self.reset_ui_state()
            self.btn_pause.config(text="暫停", state="disabled")

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
import tkinter as tk
from tkinter import messagebox
import threading
import time

# 引入您的大腦
from core import bot, action, config, vision

class SudokuBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("數獨機器人控制器")
        self.root.geometry("300x250") # 設定視窗大小 (寬x高)
        self.root.resizable(False, False) # 禁止縮放，保持介面整潔

        # 初始化控制器
        self.is_running = False # 用來防止重複點擊

        # --- 介面元件 ---

        # 1. 標題區
        self.label_status = tk.Label(root, text="準備就緒", fg="blue", font=("微軟正黑體", 12, "bold"))
        self.label_status.pack(pady=15)

        # 2. 快速按鈕區 (執行 10 次)
        self.btn_run_10 = tk.Button(root, text="🔥 直接執行 10 次", 
                                    command=lambda: self.start_thread(10),
                                    bg="#ffdddd", font=("微軟正黑體", 10), height=2)
        self.btn_run_10.pack(fill='x', padx=20, pady=5)

        # 分隔線
        tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill='x', padx=10, pady=15)

        # 3. 自訂次數區
        input_frame = tk.Frame(root)
        input_frame.pack(pady=5)

        tk.Label(input_frame, text="次數:").pack(side="left")
        
        self.entry_count = tk.Entry(input_frame, width=5, justify='center')
        self.entry_count.insert(0, "1") # 預設值 1
        self.entry_count.pack(side="left", padx=5)

        self.btn_run_custom = tk.Button(input_frame, text="▶ 開始執行", 
                                        command=self.on_click_custom_run,
                                        bg="#ddffdd")
        self.btn_run_custom.pack(side="left")

        # 4. 底部資訊
        self.lbl_info = tk.Label(root, text="按下按鈕後請勿移動滑鼠", fg="gray", font=("Arial", 8))
        self.lbl_info.pack(side="bottom", pady=5)

    def on_click_custom_run(self):
        """處理自訂次數按鈕點擊"""
        try:
            count = int(self.entry_count.get())
            if count <= 0: raise ValueError
            self.start_thread(count)
        except ValueError:
            messagebox.showerror("錯誤", "請輸入正確的數字！")

    def start_thread(self, count):
        """啟動背景執行緒 (避免視窗卡死)"""
        if self.is_running:
            messagebox.showwarning("警告", "機器人正在執行中，請稍候...")
            return

        # 鎖定按鈕
        self.is_running = True
        self.btn_run_10.config(state="disabled")
        self.btn_run_custom.config(state="disabled")
        
        # 建立執行緒並啟動
        task_thread = threading.Thread(target=self.run_logic, args=(count,))
        task_thread.daemon = True # 設定為守護執行緒，視窗關閉時會一起關閉
        task_thread.start()

    def run_logic(self, total_rounds):
        """真正跑迴圈的地方 (在背景執行)"""
        try:
            for i in range(total_rounds):
                # 更新介面文字 (需要用 invoke 或 config)
                current_round = i + 1
                self.label_status.config(text=f"🔄 正在執行: {current_round} / {total_rounds}", fg="red")
                
                # --- 呼叫控制器 ---
                print(f"\n=== GUI: 第 {current_round} 局開始 ===")
                bot.run_n_round(current_round = i, total_rounds = total_rounds)
                # ------------------

                # 如果不是最後一局，休息一下等待轉場
                if i < total_rounds - 1:
                    self.label_status.config(text=f"⏳ 等待下一局...", fg="orange")


            # 任務結束，恢復介面
            self.label_status.config(text="✅ 任務完成！", fg="green")
            self.is_running = False
            self.btn_run_10.config(state="normal")
            self.btn_run_custom.config(state="normal")
            print("=== GUI: 所有任務結束 ===")
        except Exception as e:
            # === 錯誤捕捉區 ===
            # 把錯誤印出來，方便除錯
            print(f"❌ 發生未預期的錯誤: {e}")
            import traceback
            traceback.print_exc() # 印出完整錯誤路徑
            
            # 跳出錯誤視窗通知使用者 (Optional)
            self.label_status.config(text="❌ 發生錯誤", fg="red")
            # 注意：messagebox 最好在主執行緒呼叫，但簡單用通常沒問題
            messagebox.showerror("執行錯誤", f"機器人發生錯誤停止：\n{e}")

        finally:
            # === 善後處理區 (保證執行) ===
            # 無論成功還是失敗，這裡一定會跑
            print("=== GUI: 執行緒結束，正在重置介面 ===")
            self.reset_ui_state()

    def reset_ui_state(self):
        """
        [工具函數] 將介面恢復成可按的狀態
        """
        self.is_running = False
        try:
            # 加上 try 是怕視窗已經被關掉了還去改按鈕會報錯
            self.btn_run_10.config(state="normal")
            self.btn_run_custom.config(state="normal")
        except:
            pass




















if __name__ == "__main__":
    root = tk.Tk()
    app = SudokuBotGUI(root)
    root.mainloop()
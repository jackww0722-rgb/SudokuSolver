import subprocess
import time
from typing import Optional
from . import config
from . import vision

class AppController:
    """
    負責 App 的生命週期管理 (啟動、關閉)
    """
    def __init__(self, device_serial: Optional[str] = None):
        self.device_serial = config.device_serial

    def _run_adb(self, cmd_args: list) -> None:
        """執行 ADB 指令的底層函式"""
        base_cmd = ["adb"]
        if self.device_serial:
            base_cmd.extend(["-s", self.device_serial])
        
        full_cmd = base_cmd + ["shell"] + cmd_args
        
        try:
            # 使用 subprocess.run 執行，stdout=subprocess.DEVNULL 可以隱藏雜亂輸出
            subprocess.run(
                full_cmd, 
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            print(f"指令執行失敗: {e}")

    def stop_app(self):
        """
        強制關閉 App
        :param package_name: App 的套件名稱 (例如 com.linecorp.LGSNPTW)
        """
        vision.wait_for_image(config.clear_image)

        print(f"正在關閉: {config.package_name} ...")
        self._run_adb(["am", "force-stop", config.package_name])

    def start_app(self):
        """
        啟動 App (使用 monkey 方式，無需 Activity 名稱)
        :param package_name: App 的套件名稱
        """
        print(f"正在啟動: {config.package_name} ...")
        # monkey 指令參數解釋:
        # -p: 指定 package
        # -c android.intent.category.LAUNCHER: 指定啟動類別(模擬點擊icon)
        # 1: 執行 1 次事件
        self._run_adb([
            "monkey", 
            "-p", config.package_name, 
            "-c", "android.intent.category.LAUNCHER", 
            "1"
        ])

    def restart_app(self):
        self.stop_app()
        time.sleep(3.0)
        self.start_app()

# --- 使用範例 ---
if __name__ == "__main__":
    controller = AppController()
    
    
    # 測試重啟流程
    controller.stop_app()
    
    import time
    time.sleep(2) # 等待 2 秒確保完全關閉
    
    controller.start_app()
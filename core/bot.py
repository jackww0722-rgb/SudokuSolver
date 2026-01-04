# bot.py
import copy
import time
from . import vision, solver, action, config  # 都在 core 裡，網內互打
from .app_controller import AppController

def run_n_round(current_round = 1, total_rounds = 1):
    board_numbers, region = vision.scan_board()
        
    if region:
        original_board = copy.deepcopy(board_numbers)
        print("\n🧠 正在計算...")
        if solver.solve_algo(board_numbers):
            print("✅ 計算成功！")
            
            # 使用新的相對座標填寫函式
            action.fill_result_relative(original_board, board_numbers, region)

            vision.save_screenshot()


            app = AppController()
            app.restart_app()

            if current_round < total_rounds - 1:
                    vision.wait_for_image(config.START_BUTTON_IMAGE)
                    time.sleep(3)
                    action.click_position(config.START_BUTTON_IMAGE)
                    time.sleep(1)
                    action.click_position(config.normal_diff_image, confidence=0.8)
                    time.sleep(3) 

        else:
            print("❌ 無解！請檢查識別結果。")
        return True
    else:
        print("❌ 無解！請檢查識別結果。")
        return False

    
    
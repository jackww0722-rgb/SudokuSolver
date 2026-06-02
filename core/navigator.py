class SudokuNavigator:
    def __init__(self, screen_w: int, screen_h: int, board_top_y: int):
        """
        戰術智庫：融合遊戲引擎底層的「自適應縮放邏輯」
        """
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.board_top_y = board_top_y
        
        # ==========================================
        # 🌟 核心引擎：你找回來的黃金縮放算式
        # ==========================================
        limit_w = screen_w * 0.9446  # 寬度極限模式 (正常/瘦長機型)
        limit_h = screen_h / 1.88    # 高度極限模式 (矮胖機型)

        # 1. 遊戲引擎會選擇比較小的那一個作為「真實盤面寬度」
        self.actual_board_w = min(limit_w, limit_h)

        # 2. 算出絕對精準的左右留白與單格大小
        self.margin_left = (screen_w - self.actual_board_w) / 2
        self.cell_size = self.actual_board_w / 9

        # 3. 算出按鍵的 Y 座標 (錨定螢幕底部)
        bottom_offset = self.actual_board_w * 0.31
        self.button_y = screen_h - bottom_offset
        # ==========================================

        # 建立快取口袋
        self.cell_coords = {}    
        self.button_coords = {}  
        
        # 立即計算！
        self._pre_calculate()

    def _pre_calculate(self):
        """算好 81 個格子和 9 個按鈕的座標並存入字典"""
        
        # 1. 計算盤面 81 個格子
        for row in range(9):
            for col in range(9):
                # X = 左邊界 + (第幾欄 * 格子寬) + 半個格子寬
                x = self.margin_left + (col * self.cell_size) + (self.cell_size / 2)
                # Y = 盤面頂部 (Vision給的) + (第幾列 * 格子高) + 半個格子高
                y = self.board_top_y + (row * self.cell_size) + (self.cell_size / 2)
                
                self.cell_coords[(row, col)] = (int(x), int(y))

        # 2. 計算下方 1~9 數字按鈕
        # 假設按鈕有 9 個，等距排列在底部 (這裡沿用剛剛的置中排列邏輯)
        for num in range(1, 10):
            col_index = num - 1
            x = self.margin_left + (col_index * self.cell_size) + (self.cell_size / 2)
            # 使用算好的神級 button_y
            self.button_coords[num] = (int(x), int(self.button_y))

    def get_all_positions(self) -> dict:
        """把座標地圖打包回傳"""
        return {
            "cells": self.cell_coords,
            "buttons": self.button_coords,
            "cell_size": int(self.cell_size) 
        }
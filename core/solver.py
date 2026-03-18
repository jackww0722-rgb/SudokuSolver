# core/solver.py
class BitwiseSudokuSolver:
    """
    [內部引擎] 使用位元運算 (Bitwise Operation) 來加速數獨解題
    這個類別通常由 SolverBot 呼叫，每一局會建立一個新的實例。
    """
    def __init__(self, board):
        self.board = board
        # 1. 準備狀態容器 (全部初始化為 0，代表空)
        self.rows = [0] * 9
        self.cols = [0] * 9
        self.boxes = [0] * 9
        self.empty_cells = []

        # 2. 預先處理盤面：把已知的數字轉成位元存進去
        for r in range(9):
            for c in range(9):
                val = board[r][c]
                if val != 0:
                    # 產生該數字的位元碼 (例如 1 -> 1, 2 -> 10, 3 -> 100)
                    mask = 1 << (val - 1)
                    
                    # 標記：這一列、這一行、這一個宮，都佔用這個數字了
                    self.rows[r] |= mask
                    self.cols[c] |= mask
                    self.boxes[self._get_box_index(r, c)] |= mask
                else:
                    self.empty_cells.append((r, c))

    def _get_box_index(self, r, c):
        # 計算目前格子屬於第幾個九宮格 (0~8)
        return (r // 3) * 3 + (c // 3)

    def _solve(self):
        # 如果沒有空格，代表解完了
        if not self.empty_cells:
            return True

        # ==========================================
        # MRV 優化：尋找候選數最少的空格
        # ==========================================
        min_candidates = 10
        best_index = -1
        best_candidates_bits = 0 

        # 掃描所有剩下的空格
        for i, (r, c) in enumerate(self.empty_cells):
            box_idx = self._get_box_index(r, c)
            
            # 【核心運算】合併佔用狀態
            occupied = self.rows[r] | self.cols[c] | self.boxes[box_idx]
            
            # 取反並遮罩 -> 得到所有「可填數字」
            available = ~occupied & 0x1FF
            
            if available == 0:
                return False  # 此路不通
            
            # 計算二進位中有幾個 1
            count = bin(available).count('1')

            if count < min_candidates:
                min_candidates = count
                best_index = i
                best_candidates_bits = available
                if count == 1: 
                    break 

        # ==========================================
        # 開始嘗試填入數字
        # ==========================================
        r, c = self.empty_cells.pop(best_index)
        box_idx = self._get_box_index(r, c)

        for num in range(1, 10):
            bit = 1 << (num - 1)
            
            if best_candidates_bits & bit:
                # 1. 填入狀態
                self.rows[r] |= bit
                self.cols[c] |= bit
                self.boxes[box_idx] |= bit
                self.board[r][c] = num

                # 2. 遞迴
                if self._solve():
                    return True

                # 3. 回溯 (XOR 清除)
                self.rows[r] ^= bit
                self.cols[c] ^= bit
                self.boxes[box_idx] ^= bit
                self.board[r][c] = 0

        self.empty_cells.insert(best_index, (r, c))
        return False

# ==========================================
# 🚀 對外接口類別
# ==========================================
class SolverBot:
    def __init__(self):
        # 這裡不需要做什麼初始化，因為演算法是無狀態的 (Stateless)
        pass

    def solve(self, board_numbers):
        """
        接收 9x9 的二維陣列 (包含 0)，回傳解答後的陣列。
        如果無解，回傳 None。
        """
        print(f"SolverBot 開始計算...")
        
        # 為了不影響原始輸入，建議複製一份 (雖然 bot.py 已經有備份，但在這裡做更保險)
        # 不過因為 BitwiseSudokuSolver 是直接修改傳入的物件，
        # 如果要在 solve() 失敗時不污染原陣列，最好用 deepcopy。
        # 但考慮到我們只在成功時才回傳，且 bot.py 已經有 original_board 備份，這裡直接傳也行。
        # 為了安全起見，我們還是做個淺拷貝給引擎跑
        
        # 注意：board_numbers 是 List of Lists，需要 deepcopy 才能完全隔離
        # 但因為我們想要效能，且 bot.py 已經 handle 了 original，
        # 這裡我們直接對 board_numbers 操作，成功就回傳它，失敗回傳 None。
        
        engine = BitwiseSudokuSolver(board_numbers)
        
        if engine._solve():
            # engine.solve() 會直接修改 board_numbers 變成答案
            return board_numbers
        else:
            return None
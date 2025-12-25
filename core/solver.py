# solver.py



# ==========================================
# 🧠 數獨演算法 (升級版 - 秒解難題)
# ==========================================

def is_valid(board, num, pos):
    # 檢查行
    for i in range(9):
        if board[pos[0]][i] == num and pos[1] != i: return False
    # 檢查列
    for i in range(9):
        if board[i][pos[1]] == num and pos[0] != i: return False
    # 檢查九宮格
    box_x, box_y = pos[1] // 3, pos[0] // 3
    for i in range(box_y*3, box_y*3 + 3):
        for j in range(box_x*3, box_x*3 + 3):
            if board[i][j] == num and (i,j) != pos: return False
    return True

def solve_algo(board):
    """
    智慧型解題：優先找「候選數字最少」的格子填寫 (MRV 演算法)
    這能讓原本要算很久的難題瞬間解開。
    """
    empty_pos = find_best_empty(board)
    
    # 如果找不到空格，代表解完了
    if not empty_pos:
        return True
    
    row, col, candidates = empty_pos
    
    # 嘗試填入候選數字
    for num in candidates:
        board[row][col] = num
        if solve_algo(board):  #假設後面也填得上
            return True
        
    board[row][col] = 0 # 回溯    
    return False  #進不去 怎麼想都進不去 前面給我重來

def find_best_empty(board):
    """
    尋找所有空格中，最容易填的那一格 (候選數字最少的)
    回傳格式: (row, col, [可填數字列表])
    """
    best_pos = None
    min_candidates_count = 10 # 初始值設比 9 大
    best_candidates = []
    
    found_empty = False
    
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                found_empty = True
                
                # 計算這格可以填哪些數字
                candidates = []
                for num in range(1, 10):
                    if is_valid(board, num, (r, c)):
                        candidates.append(num)
                
                # 如果發現某格無解 (0 個候選)，直接回傳該格讓上層回溯
                if len(candidates) == 0:
                    return (r, c, [])
                
                # 如果這格的選擇比目前的最佳選擇還少，就選它
                if len(candidates) < min_candidates_count:
                    min_candidates_count = len(candidates)
                    best_candidates = candidates
                    best_pos = (r, c)
                    
                    # 優化：如果只剩 1 個選擇，那是必填項，直接回傳不用再找了
                    if min_candidates_count == 1:
                        return (r, c, best_candidates)

    if not found_empty:
        return None # 沒有空格了
        
    return (best_pos[0], best_pos[1], best_candidates)
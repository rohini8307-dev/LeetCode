class Solution(object):
    def isValidSudoku(self, board):
        rows=[set() for i in range(9)]
        cols=[set() for i in range(9)]
        boxs=[set() for i in range(9)]
        for r in range(9):
            for c in range(9):
                num=board[r][c]
                if num=='.':
                    continue
                box=(r//3)*3+(c//3)
                if num in rows[r] or num in cols[c] or num in boxs[box]:
                    return False
                rows[r].add(num)
                cols[c].add(num)
                boxs[box].add(num)
        return True        

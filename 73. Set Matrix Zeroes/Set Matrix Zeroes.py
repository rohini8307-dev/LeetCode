class Solution(object):
    def setZeroes(self, matrix):
        r=len(matrix)
        c=len(matrix[0])
        rows=set()
        cols=set()
        for a in range(r):
            for b in range(c):
                if matrix[a][b]==0:
                    rows.add(a)
                    cols.add(b)

        for a in range(r):
            for b in range(c):
                if a in rows or b in cols:
                    matrix[a][b]=0           
        return matrix 
        

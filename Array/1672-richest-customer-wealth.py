class Solution(object):
    def maximumWealth(self, accounts):
        m=0
        for i in accounts:
            t=0
            for j in i:
                t+=j
            m=max(m,t)
        return m

class Solution(object):
    def maximumCount(self, nums):
        e=0
        n=0
        for i in nums:
            if i>0:
                e+=1
            elif i<0:
                n+=1
        return max(e,n)
        

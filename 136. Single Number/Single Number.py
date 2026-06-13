class Solution(object):
    def singleNumber(self, nums):
        freq={}
        for i in nums:
            freq[i]=freq.get(i,0)+1
        for i in freq:
            if freq[i]==1:
                return i        

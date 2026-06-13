class Solution(object):
    def majorityElement(self, nums):
        c=0
        ca=None
        for n in nums:
            if c==0:
                ca=n
            if n==ca:
                c+=1
            else:
                c-=1
        return ca
        

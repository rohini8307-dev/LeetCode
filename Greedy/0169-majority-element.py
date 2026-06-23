class Solution:
    def majorityElement(self, nums: List[int]) -> int:
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

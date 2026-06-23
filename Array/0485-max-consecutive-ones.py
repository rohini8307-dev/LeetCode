class Solution:
    def findMaxConsecutiveOnes(self, nums: List[int]) -> int:
        c=0
        ans=0
        for n in nums:
            if n==1:
                c+=1
                ans=max(ans,c)
            else:
                c=0
        return ans

class Solution:
    def longestOnes(self, nums: List[int], k: int) -> int:
        l=0
        ans=0
        z=0
        for i in range(len(nums)):
            if nums[i]==0:
                z+=1
            while z>k:
                if nums[l]==0:
                    z-=1
                l+=1
            ans=max(ans,i-l+1)
        return ans


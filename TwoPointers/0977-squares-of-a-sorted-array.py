class Solution:
    def sortedSquares(self, nums: List[int]) -> List[int]:
        n=len(nums)
        a=[0]*n
        l=0
        r=n-1
        k=n-1
        while l<=r:
            if nums[l]**2>nums[r]**2:
                a[k]=nums[l]**2
                l+=1
            else:
                a[k]=nums[r]**2
                r-=1
            k-=1
        return a

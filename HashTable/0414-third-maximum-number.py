class Solution:
    def thirdMax(self, nums: List[int]) -> int:
        nums=set(nums)
        a1=max(nums)
        nums.remove(a1)
        if len(nums)!=0:
            a=max(nums)
            nums.remove(a)
        if len(nums)!=0:
            a=max(nums)
            return a
        return a1

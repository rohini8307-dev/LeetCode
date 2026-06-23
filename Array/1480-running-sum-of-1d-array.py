class Solution(object):
    def runningSum(self, nums):
        a=[0]*len(nums)
        for i in range(len(nums)):
            if i==0:
                a[i]=nums[i]
                continue
            a[i]=nums[i]+a[i-1]
        return a

class Solution(object):
    def twoSum(self, nums, target):
        k={}
        for i,num in enumerate(nums):
            c=target - num
            if c in k:
                return [k[c],i]
            k[num]=i

        

class Solution(object):
    def findNumbers(self, nums):
        o=0
        for i in nums:
            if len(str(i))%2==0:
                o+=1
        return o

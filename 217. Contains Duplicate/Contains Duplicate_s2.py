class Solution(object):
    def containsDuplicate(self, nums):
        t=set()
        for n in nums:
            if n in t:
                return True
            t.add(n)
        return False

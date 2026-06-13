class Solution(object):
    def intersection(self, nums1, nums2):
        a=set(nums1)
        b=set()
        for i in nums2:
            if i in a:
                b.add(i)
        return list(b)        

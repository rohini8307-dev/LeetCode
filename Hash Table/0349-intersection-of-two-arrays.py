class Solution:
    def intersection(self, nums1: List[int], nums2: List[int]) -> List[int]:
        a=set(nums1)
        b=set()
        for i in nums2:
            if i in a:
                b.add(i)
        return list(b)

class Solution:
    def topKFrequent(self, nums: List[int], k: int) -> List[int]:
        if len(nums)<=1:
            return nums
        l={}
        for i in nums:
            l[i]=l.get(i,0)+1
        a=[[] for i in range(len(nums)+1)]
        for i in l:
            a[l[i]].append(i)
        an=[]
        for j in range(len(nums),-1,-1):
            for i in a[j]:
                an.append(i)
            if len(an)==k:
                return an

class Solution(object):
    def intersect(self, nums1, nums2):
        a={}
        if len(nums1)>len(nums2):
            nums1,nums2=nums2,nums1
        for i in nums1:
            a[i]=a.get(i,0)+1
        k=[]
        for i in nums2:
            if i in a and a[i]>0:
                k.append(i)
                a[i]-=1
        return k

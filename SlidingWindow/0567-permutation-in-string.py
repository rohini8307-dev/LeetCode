class Solution:
    def checkInclusion(self, s1: str, s2: str) -> bool:
        if len(s1)>len(s2):
            return False
        k=len(s1)
        need={}
        for i in s1:
            need[i]=need.get(i,0)+1
        w={}
        for i in range(k):
            w[s2[i]]=w.get(s2[i],0)+1
        l=0
        if w==need:
            return True
        for i in range(k,len(s2)):
            w[s2[i]]=w.get(s2[i],0)+1
            w[s2[l]]-=1
            if w[s2[l]]==0:
                del w[s2[l]]
            if w==need:
                return True
            l+=1
        return False

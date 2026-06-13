class Solution(object):
    def isAnagram(self, s, t):
        if len(s)!=len(t):
            return False
        k={}
        for i in s:
            k[i]=k.get(i,0)+1
        for i in t:
            if i not in k:
                return False
            k[i]-=1
            if k[i]<0:
                return False
        return True

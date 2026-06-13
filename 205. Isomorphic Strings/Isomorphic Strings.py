class Solution(object):
    def isIsomorphic(self, s, t):
        a={}
        b={}
        for i in range(len(s)):
            c=s[i]
            d=t[i]
            if c in a and a[c]!=d:
                return False
            if d in b and b[d]!=c:
                return False
            a[c]=d
            b[d]=c
        return True
        

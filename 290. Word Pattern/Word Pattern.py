class Solution(object):
    def wordPattern(self, pattern, s):
        s=s.split()
        if len(s)!=len(pattern):
            return False
        a={}
        b={}
        for i in range(len(s)):
            c=pattern[i]
            d=s[i]
            if c in a and a[c]!=d:
                return False
            if d in b and b[d]!=c:
                return False
            a[c]=d
            b[d]=c
        return True

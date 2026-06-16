class Solution:
    def reverseVowels(self, s: str) -> str:
        i=0
        s=list(s)
        j=len(s)-1
        p="aeiouAEIOU"
        while i<j:
            if s[i] in p and s[j] in p:
                s[i],s[j]=s[j],s[i]
                i+=1
                j-=1
            elif s[i] not in p:
                i+=1
            elif s[j] not in p: 
                j-=1
        return "".join(s)
        

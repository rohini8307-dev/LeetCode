class Solution:
    def isPalindrome(self, s: str) -> bool:
        p=""
        for i in s:
            if i.isalnum():
                p+=i.lower()
        i=0
        j=len(p)-1
        while i<j:
            if p[i]!=p[j]:
                return False
            i+=1
            j-=1
        return True
        

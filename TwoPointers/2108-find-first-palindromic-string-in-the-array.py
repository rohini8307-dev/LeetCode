class Solution:
    def firstPalindrome(self, words: List[str]) -> str:
        for k in words:
            i=0
            j=len(k)-1
            l=1
            while i<j:
                if k[i]!=k[j]:
                    l=0
                    break
                i+=1
                j-=1
            if l:
                return k
        return ""

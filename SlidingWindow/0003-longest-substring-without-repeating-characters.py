class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        ans=0
        l=0
        w=set()
        for i in range(len(s)):
            while s[i] in w:
                w.remove(s[l])
                l+=1
            w.add(s[i])
            ans=max(ans,i-l+1)
        return ans
                

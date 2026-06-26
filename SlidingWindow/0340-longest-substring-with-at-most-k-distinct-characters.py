class Solution:
    def longestKSubstr(self, s, k):
        w={}
        ans=-1
        l=0
        for i in range(len(s)):
            w[s[i]]=w.get(s[i],0)+1
            while len(w)>k:
                w[s[l]]-=1
                if w[s[l]]==0:
                    del w[s[l]]
                l+=1
            if len(w)==k:
                ans=max(ans,i-l+1)
        return ans
            
    
        
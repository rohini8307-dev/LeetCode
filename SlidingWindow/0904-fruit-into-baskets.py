class Solution:
    def totalFruit(self, fruits: List[int]) -> int:
        ans=0
        l=0
        freq={}
        for r in range(len(fruits)):
            freq[fruits[r]]=freq.get(fruits[r],0)+1
            while len(freq)>2:
                k=fruits[l]
                freq[k]-=1
                if freq[k]==0:
                    del freq[k]
                l+=1
            ans=max(ans,r-l+1)
        return ans
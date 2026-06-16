class Solution:
    def maxProfit(self, prices: List[int]) -> int:
        m=prices[0]
        mp=0
        for i in range(1,len(prices)):
            if prices[i]<m:
                m=prices[i]
                continue
            else:
                mp=max(mp,prices[i]-m)

        return mp

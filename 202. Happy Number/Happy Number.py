class Solution:
    def isHappy(self, n: int) -> bool:
        k=set()
        while n!=1 and n not in k:
            k.add(n)
            r=0 
            while n>0:
                r+=(n%10)**2
                n//=10
            n=r
        if n==1:
            return True
        else:
            return False

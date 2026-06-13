class Solution(object):
    def canConstruct(self, ransomNote, magazine):
        if len(magazine)<len(ransomNote):
            return False
        k={}
        for i in magazine:
            k[i]=k.get(i,0)+1
        for i in ransomNote:
            if i not in k:
                return False
            k[i]-=1
            if k[i]<0:
                return False
        return True

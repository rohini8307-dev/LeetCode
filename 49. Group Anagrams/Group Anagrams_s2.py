class Solution(object):
    def groupAnagrams(self, strs):
        d={}
        for i in strs:
            c=[0]*26
            for ch in i:
                c[ord(ch)-ord('a')]+=1
            k=tuple(c)
            if k not in d:
                d[k]=[]
            d[k].append(i)
        return d.values()
        

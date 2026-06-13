class Solution(object):
    def groupAnagrams(self, strs):
        d={}
        for i in strs:
            k="".join(sorted(i))
            if k not in d:
                d[k]=[]
            d[k].append(i)
        return d.values()

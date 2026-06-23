class Solution:
    def insert(self, intervals: List[List[int]], newInterval: List[int]) -> List[List[int]]:
        ans=[]
        for s,e in intervals:
            if e<newInterval[0]:
                ans.append([s,e])
            elif s>newInterval[1]:
                ans.append(newInterval)
                newInterval=[s,e]
            else:
                newInterval=[
                    min(s,newInterval[0]),
                    max(e,newInterval[1])
                ]
        ans.append(newInterval)
        return ans

"""Resolution-independent image-space approximation of the ego driving corridor."""
from dataclasses import dataclass
from enum import Enum

class PathLevel(str, Enum): NONE='NONE'; LOW='LOW'; MEDIUM='MEDIUM'; HIGH='HIGH'
@dataclass(frozen=True)
class PathRelevance:
    score: float; level: PathLevel; in_path: bool; reason: str
@dataclass(frozen=True)
class EgoPathModel:
    bottom_width: float=.55; top_width: float=.16; horizon_y: float=.42; center_offset: float=0.0
    def _bounds(self,y):
        progress=min(1,max(0,(y-self.horizon_y)/(1-self.horizon_y)))
        width=self.top_width+(self.bottom_width-self.top_width)*progress
        center=.5+self.center_offset
        return center-width/2, center+width/2
    def relevance_for_bbox(self,bbox,width,height):
        x1,y1,x2,y2=bbox; x=(x1+x2)/2/width; y=y2/height; left,right=self._bounds(y)
        if left<=x<=right:
            score=1-abs(x-(left+right)/2)/(max(.001,(right-left)/2)); level=PathLevel.HIGH if score>.7 else PathLevel.MEDIUM
            return PathRelevance(score,level,True,'bbox lower centre is inside ego corridor')
        gap=min(abs(x-left),abs(x-right)); score=max(0,1-gap/.2)
        return PathRelevance(score,PathLevel.LOW if score else PathLevel.NONE,False,'bbox lower centre is outside ego corridor')

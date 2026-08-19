"""Explainable lead-object selection for image or simulator standardized objects."""
def select_lead(candidates):
    hazards=[c for c in candidates if c.is_hazard]
    if not hazards: return None
    # Known distance wins; otherwise path relevance/persistence/box area wins.
    def score(c):
        p=c.perception; area=(p.bbox[2]-p.bbox[0])*(p.bbox[3]-p.bbox[1]) if p.bbox else 0
        return (0 if p.distance_m is None else 1, -(p.distance_m or 0), c.persistence_frames, area, p.confidence)
    return max(hazards,key=score)

from safar.hazard.ttc import calculate_ttc_s
from safar.hazard.lead import select_lead
from safar.hazard.models import PerceptionObject, HazardCandidate
from safar.perception.image_tracker import ImageTracker
from safar.perception.types import SAFARDetection

def test_tracker_keeps_id_and_expires_stale_track():
    t=ImageTracker(max_missed=1); first=t.update([SAFARDetection('car',.9,(1,1,20,20),'vehicle')])[0]
    assert t.update([SAFARDetection('car',.9,(2,1,21,20),'vehicle')])[0].track_id==first.track_id
    t.update([]); assert not t.update([])
def test_ttc_only_for_valid_closing_values():
    assert round(calculate_ttc_s(20,36),1)==2.0
    assert calculate_ttc_s(20,0) is None and calculate_ttc_s(None,20) is None
def test_lead_prefers_relevant_persistent_object_over_confidence():
    a=HazardCandidate(PerceptionObject('lead','vehicle',.5,'x',True,bbox=(400,1,600,500)),3,True,'')
    b=HazardCandidate(PerceptionObject('side','vehicle',.99,'x',True,bbox=(1,1,100,100)),2,True,'')
    assert select_lead([a,b]).perception.object_id=='lead'

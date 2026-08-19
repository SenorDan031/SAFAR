from safar.perception.ego_path import EgoPathModel, PathLevel
def test_centered_box_is_relevant_at_any_resolution():
    p=EgoPathModel(); assert p.relevance_for_bbox((450,200,550,700),1000,800).in_path
    assert p.relevance_for_bbox((900,200,990,700),1000,800).level==PathLevel.NONE

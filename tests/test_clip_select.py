import pytest
from clipforge.clip_select import parse_clips, evenly_spaced, manual_clip


def test_valid():
    assert parse_clips({"clips": [{"start": 1, "end": 25, "hook": "A complete idea", "score": 80}]}, 60, 3)[0].start == 1


@pytest.mark.parametrize("start,end,score", [(0,19,80),(-1,25,80),(40,70,80),(0,25,101),(0,float('nan'),80)])
def test_invalid(start,end,score):
    with pytest.raises(ValueError):
        parse_clips({"clips": [{"start":start,"end":end,"hook":"Hook","score":score}]},60,3)


def test_overlap():
    with pytest.raises(ValueError):
        parse_clips({"clips": [{"start":0,"end":25,"hook":"A","score":80},{"start":20,"end":45,"hook":"B","score":90}]},60,3)


def test_evenly_spaced():
    clips=evenly_spaced(200,3,20,30)
    assert len(clips)==3 and clips[-1].end==200
    assert all(c.end-c.start==30 for c in clips)
    assert all(a.end<=b.start for a,b in zip(clips,clips[1:]))


def test_insufficient_and_manual_bounds():
    with pytest.raises(ValueError): evenly_spaced(65,5,20,30)
    assert manual_clip(10,25,60).end==35
    for start,length in [(-1,25),(0,19),(50,25),(0,float('nan'))]:
        with pytest.raises(ValueError): manual_clip(start,length,60)

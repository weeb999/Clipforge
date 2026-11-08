from clipforge.subtitles import generate, timestamp


def test_word_highlight_and_offsets():
    words=[{"start":10,"end":10.5,"word":"One"},{"start":10.5,"end":11,"word":"two"},{"start":11,"end":11.5,"word":"three"}]
    ass=generate(words,10,30,"Classic White","Inter",1080,1920)
    assert "PlayResY: 1920" in ass
    assert "0:00:00.00,0:00:00.50" in ass
    assert ass.count("Dialogue:")==3
    assert r"\1c&H0000FFFF&}One" in ass


def test_escape_and_clip_bounds():
    ass=generate([{"start":0,"end":3,"word":r"{\bad}"}],1,2,"Minimal Black Box","Inter",1080,1080)
    assert r"\{" in ass
    assert "0:00:00.00,0:00:01.00" in ass
    assert timestamp(59.999)=="0:01:00.00"

import pytest
from clipforge.editing import apply_edits

WORDS=[{'word':'one','start':0,'end':.5},{'word':'two','start':.6,'end':1},{'word':'three','start':1.1,'end':1.5},{'word':'four','start':2,'end':2.5}]


def test_unchanged_text_preserves_word_timing():
    assert apply_edits(WORDS,'one two three\nfour\n')==WORDS


def test_changed_phrase_keeps_interval_and_other_words():
    result=apply_edits(WORDS,'corrected phrase\nfour\n')
    assert result[0]['start']==0 and result[1]['end']==1.5
    assert result[-1]==WORDS[-1]


def test_delete_phrase_and_line_count():
    assert apply_edits(WORDS,'\nfour\n')==[WORDS[-1]]
    with pytest.raises(ValueError): apply_edits(WORDS,'one line')

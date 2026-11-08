import sys
from contextlib import nullcontext
from types import SimpleNamespace
import pytest
from clipforge.transcribe import transcribe


def fake_engine(monkeypatch,tmp_path):
    monkeypatch.setenv('CLIPFORGE_HOME',str(tmp_path/'state'))
    path=tmp_path/'audio.mp4'; path.write_bytes(b'audio')
    calls=[]
    monkeypatch.setitem(sys.modules,'av',SimpleNamespace(open=lambda path:nullcontext(SimpleNamespace(streams=SimpleNamespace(audio=[1])))))
    class Model:
        def __init__(self,*args,**kwargs): pass
        def transcribe(self,path,**kwargs):
            calls.append(kwargs)
            return [SimpleNamespace(words=[SimpleNamespace(start=0,end=1,word=' Hello ')])],None
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(WhisperModel=Model))
    return path,calls


def test_english_translation_and_cache_isolation(tmp_path,monkeypatch):
    path,calls=fake_engine(monkeypatch,tmp_path)
    original=transcribe(path,source_language='ar',caption_language='original')
    assert calls[-1]['language']=='ar' and calls[-1]['task']=='transcribe'
    english=transcribe(path,source_language='ar',caption_language='en')
    assert calls[-1]['task']=='translate' and calls[-1]['language']=='ar'
    assert transcribe(path,source_language='ar',caption_language='en')==english
    assert len(calls)==2 and len(list((tmp_path/'state/cache').glob('*.json')))==2


def test_forced_english_avoids_wrong_language_detection(tmp_path,monkeypatch):
    path,calls=fake_engine(monkeypatch,tmp_path)
    transcribe(path,source_language='en')
    assert calls[0]['language']=='en' and calls[0]['task']=='transcribe'
    assert calls[0]['condition_on_previous_text'] is False


def test_auto_translation_and_invalid_model(tmp_path,monkeypatch):
    path,calls=fake_engine(monkeypatch,tmp_path)
    transcribe(path)
    assert calls[0]['language'] is None and calls[0]['task']=='translate'
    with pytest.raises(ValueError): transcribe(path,'base.en',source_language='ar')


def test_lyrics_does_not_filter_singing_as_silence(tmp_path,monkeypatch):
    path,calls=fake_engine(monkeypatch,tmp_path)
    transcribe(path,source_language='ar',vad_filter=False)
    assert calls[0]['vad_filter'] is False and calls[0]['task']=='translate'
    transcribe(path,source_language='ar',vad_filter=True)
    assert len(calls)==2

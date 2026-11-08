import sys
from types import SimpleNamespace
from clipforge.reframe import face_track
from contextlib import nullcontext


def test_missing_cascade_uses_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules, 'cv2', SimpleNamespace())
    assert face_track(None,0,20)==[]


def test_empty_detector_uses_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules, 'cv2', SimpleNamespace(
        data=SimpleNamespace(haarcascades='missing/'),
        CascadeClassifier=lambda path: SimpleNamespace(empty=lambda: True)))
    assert face_track(None,0,20)==[]


def test_default_fit_never_runs_face_crop(monkeypatch,tmp_path):
    from clipforge import reframe
    from clipforge.clip_select import Clip
    calls=[]
    monkeypatch.setattr(reframe,'probe',lambda path:(60,640,360))
    monkeypatch.setattr(reframe,'face_track',lambda *args:(_ for _ in ()).throw(AssertionError('Fit must never crop to a face')))
    monkeypatch.setitem(sys.modules,'av',SimpleNamespace(open=lambda path:nullcontext(SimpleNamespace(streams=SimpleNamespace(audio=[1])))))
    monkeypatch.setattr(reframe,'command',lambda args,**kwargs:calls.append(args))
    monkeypatch.setattr(reframe,'ffmpeg',lambda:'ffmpeg')
    reframe.cut(tmp_path/'source.mp4',Clip(0,20,'test',0),tmp_path/'out.mp4','9:16')
    filters=calls[0][calls[0].index('-filter_complex')+1]
    assert 'pad=1080:1920' in filters and 'crop=' not in filters

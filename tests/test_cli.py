import json
import pytest
from clipforge.cli import parser, resolve_source, run


def test_unattended_flags():
    args=parser().parse_args(['run','--demo','--yes','--theme','Neon Glow','--font','Inter','--clips','3'])
    assert args.yes and args.demo and args.clips==3


@pytest.mark.parametrize('command',['queue','daemon','post-due','auth'])
def test_no_publishing_commands(command):
    with pytest.raises(SystemExit): parser().parse_args([command])


def test_source_file_and_conflicts(tmp_path):
    source=tmp_path/'my video.mp4'; source.write_bytes(b'video')
    assert resolve_source(str(source),None)==source
    with pytest.raises(ValueError): resolve_source(str(source),str(source))
    with pytest.raises(ValueError,match='only to YouTube'): resolve_source(str(source),None,cookies_from_browser='edge')


def test_authentication_flags():
    args=parser().parse_args(['run','https://youtu.be/abc','--cookies-from-browser','edge:Profile 1'])
    assert args.cookies_from_browser=='edge:Profile 1'
    with pytest.raises(SystemExit):
        parser().parse_args(['run','https://youtu.be/abc','--cookies-from-browser','edge','--cookies','cookies.txt'])


def test_url_dispatch(monkeypatch,tmp_path):
    import clipforge.download
    seen=[]
    monkeypatch.setattr(clipforge.download,'download',lambda url,**kwargs: seen.append(url) or tmp_path/'download.mp4')
    resolve_source('https://example.org/sample.mp4',None)
    assert seen==['https://example.org/sample.mp4']


@pytest.mark.parametrize('captions',['on','off'])
@pytest.mark.parametrize('visual',[False,True])
def test_local_export_never_creates_queue(tmp_path,monkeypatch,captions,visual):
    import clipforge.transcribe
    import clipforge.reframe
    import clipforge.subtitles
    import clipforge.gallery
    if visual:
        monkeypatch.setattr(clipforge.gallery,'choose_style',lambda initial,source:{**initial,'font':'Anton','theme':'Neon Glow','framing':'blur','source_language':'ar','caption_language':'en'})
    monkeypatch.setenv('CLIPFORGE_HOME',str(tmp_path/'state'))
    monkeypatch.setenv('CLIPFORGE_FFMPEG','unused-in-mocked-render')
    monkeypatch.delenv('LLM_API_KEY',raising=False)
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.setattr(clipforge.reframe,'probe',lambda path:(65,640,360))
    monkeypatch.setattr(clipforge.reframe,'cut',lambda source,clip,out,aspect,**kwargs:out.write_bytes(b'raw'))
    def render(source,ass,out,preview,preview_only=False):
        preview.write_bytes(b'png')
        if not preview_only: out.write_bytes(b'final')
    monkeypatch.setattr(clipforge.subtitles,'render',render)
    calls=[]
    monkeypatch.setattr(clipforge.transcribe,'transcribe',lambda *args,**kwargs: calls.append(kwargs) or [{'word':'hello','start':1,'end':2}])
    video=tmp_path/'input.mp4'; video.write_bytes(b'source')
    output=tmp_path/'export'
    monkeypatch.setattr('clipforge.cli.choose', lambda *args, **kwargs: pytest.fail('Default run must not prompt'))
    args=parser().parse_args(['run',str(video),'--selection','even','--captions',captions,'--output',str(output)])
    args.templates=visual
    run(args)
    manifest=json.loads((output/'manifest.json').read_text())
    assert (output/'clip-1.mp4').read_bytes()==b'final'
    assert manifest[0]['captions']==captions
    assert not {'scheduled','queue_id','copy','owner'} & manifest[0].keys()
    assert not list((tmp_path/'state').glob('*.sqlite3'))
    assert bool(calls)==(captions=='on')
    assert len(manifest) == 1
    assert manifest[0]['format'] == '4:5'
    assert manifest[0]['framing']==('blur' if visual else 'studio')
    if visual:
        assert manifest[0]['font']=='Anton' and manifest[0]['source_language']=='ar'
    assert manifest[0]['caption_language']=='en'
    if calls:
        assert calls[0]['caption_language']=='en'

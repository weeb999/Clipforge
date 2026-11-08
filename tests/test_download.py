import httpx
import pytest
from clipforge.download import download, javascript_runtimes, cookie_options, YouTubeLoginRequired
from types import SimpleNamespace


def test_direct_mp4_atomic_download_and_cache(tmp_path,monkeypatch):
    monkeypatch.setenv('CLIPFORGE_HOME',str(tmp_path))
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,content=b'mp4-data')
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(httpx,'stream',client.stream)
        path=download('https://example.org/video.mp4?version=1')
        assert path.read_bytes()==b'mp4-data'
        assert download('https://example.org/video.mp4?version=1')==path
    assert len(requests)==1
    assert not list(tmp_path.rglob('*.part'))


def test_failed_mp4_is_not_cached(tmp_path,monkeypatch):
    monkeypatch.setenv('CLIPFORGE_HOME',str(tmp_path))
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(403))) as client:
        monkeypatch.setattr(httpx,'stream',client.stream)
        with pytest.raises(httpx.HTTPStatusError): download('https://example.org/video.mp4')
    assert not list(tmp_path.rglob('complete.json'))
    assert not list(tmp_path.rglob('*.part'))


def test_enables_installed_node(monkeypatch):
    monkeypatch.setattr('clipforge.download.shutil.which',lambda name:'node.exe' if name=='node' else None)
    monkeypatch.setattr('clipforge.download.subprocess.run',lambda *args,**kwargs:SimpleNamespace(returncode=0,stdout='v22.12.0'))
    assert javascript_runtimes()=={'node':{'path':'node.exe'}}


def test_old_node_gets_clear_error(monkeypatch):
    monkeypatch.setattr('clipforge.download.shutil.which',lambda name:'node.exe' if name=='node' else None)
    monkeypatch.setattr('clipforge.download.subprocess.run',lambda *args,**kwargs:SimpleNamespace(returncode=0,stdout='v20.0.0'))
    with pytest.raises(RuntimeError,match='Node.js 22'): javascript_runtimes()


def test_cookie_options_are_explicit_and_exclusive(tmp_path):
    assert cookie_options()=={}
    assert cookie_options('edge:Profile 1')=={'cookiesfrombrowser':('edge','Profile 1')}
    path=tmp_path/'cookies.txt'; path.write_text('# Netscape HTTP Cookie File\n')
    assert cookie_options(cookies=str(path))=={'cookiefile':str(path)}
    with pytest.raises(ValueError): cookie_options('edge',str(path))
    with pytest.raises(ValueError): cookie_options('unknown-browser')


@pytest.mark.parametrize('browser',[None,'edge:Profile 1'])
def test_youtube_forwards_only_requested_cookies(tmp_path,monkeypatch,browser):
    monkeypatch.setenv('CLIPFORGE_HOME',str(tmp_path/'state'))
    monkeypatch.setattr('clipforge.download.ffmpeg',lambda:'ffmpeg')
    monkeypatch.setattr('clipforge.download.javascript_runtimes',lambda:{'node':{}})
    seen=[]
    class FakeDownloader:
        def __init__(self,options):
            seen.append(options)
            self.path=options['outtmpl'].replace('%(ext)s','mp4')
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def extract_info(self,*args,**kwargs):
            from pathlib import Path
            Path(self.path).write_bytes(b'video')
            return {}
        def prepare_filename(self,info): return self.path
    monkeypatch.setattr('yt_dlp.YoutubeDL',FakeDownloader)
    assert download('https://youtu.be/abc',cookies_from_browser=browser).read_bytes()==b'video'
    if browser:
        assert seen[0]['cookiesfrombrowser']==('edge','Profile 1')
    else:
        assert 'cookiesfrombrowser' not in seen[0] and 'cookiefile' not in seen[0]


def test_bot_check_has_actionable_error(tmp_path,monkeypatch):
    from yt_dlp.utils import DownloadError
    monkeypatch.setenv('CLIPFORGE_HOME',str(tmp_path))
    monkeypatch.setattr('clipforge.download.ffmpeg',lambda:'ffmpeg')
    monkeypatch.setattr('clipforge.download.javascript_runtimes',lambda:{'node':{}})
    class Blocked:
        def __init__(self,*args): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def extract_info(self,*args,**kwargs): raise DownloadError('Sign in to confirm you are not a bot')
    monkeypatch.setattr('yt_dlp.YoutubeDL',Blocked)
    with pytest.raises(YouTubeLoginRequired,match='--cookies-from-browser edge'):
        download('https://youtu.be/blocked')
    assert not list(tmp_path.rglob('complete.json'))


def test_cookies_not_sent_to_mp4(tmp_path,monkeypatch):
    monkeypatch.setenv('CLIPFORGE_HOME',str(tmp_path))
    with pytest.raises(ValueError,match='only to YouTube'):
        download('https://example.org/video.mp4',cookies_from_browser='edge')

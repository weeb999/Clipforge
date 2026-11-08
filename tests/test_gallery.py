import json
from clipforge.gallery import FONT_FILES,DEFAULTS,load_style,font_file,preview,font_sample,contact_sheet
from clipforge.themes import FONTS,THEMES


def test_every_font_asset_and_preview():
    assert set(FONT_FILES)==set(FONTS)
    for font in FONTS:
        assert font_file(font).is_file()
        assert font_sample(font).size==(290,66)
    for theme in THEMES:
        assert preview({**DEFAULTS,'theme':theme}).size==(300,460)


def test_style_validation(tmp_path,monkeypatch):
    monkeypatch.setenv('CLIPFORGE_HOME',str(tmp_path))
    (tmp_path/'style.json').write_text(json.dumps({'font':'not-a-font','framing':'blur','caption_language':'en'}))
    assert load_style()['font']=='Inter'
    assert load_style()['framing']=='blur'


def test_contact_sheet(tmp_path):
    path=contact_sheet(tmp_path/'templates.png')
    from PIL import Image
    with Image.open(path) as image:
        assert image.size==(1200,1380)

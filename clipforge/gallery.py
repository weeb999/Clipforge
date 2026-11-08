"""Local visual template picker. Uses native Tk windows, never a web server."""
import json
from pathlib import Path
from .config import home
from .themes import FONTS, THEMES
from .reframe import FORMATS, FRAMING, STUDIO_BACKGROUND, studio_caption_margin, studio_region

FONT_FILES = dict(zip(FONTS, ['Montserrat[wght].ttf', 'Poppins-Bold.ttf', 'BebasNeue-Regular.ttf', 'Anton-Regular.ttf', 'Oswald[wght].ttf', 'Bangers-Regular.ttf', 'RobotoCondensed[wght].ttf', 'Inter[opsz,wght].ttf', 'PlayfairDisplay[wght].ttf', 'Lobster-Regular.ttf', 'LuckiestGuy-Regular.ttf', 'ArchivoBlack-Regular.ttf', 'PermanentMarker-Regular.ttf']))
PRESETS = {
    'editorial': {'font': 'Inter', 'theme': 'Editorial', 'format': '4:5', 'framing': 'studio'},
    'cinema': {'font': 'Playfair Display', 'theme': 'Cinema', 'format': '16:9', 'framing': 'fit'},
    'minimal': {'font': 'Inter', 'theme': 'Minimal', 'format': '9:16', 'framing': 'studio'},
}
DEFAULTS = {**PRESETS['editorial'], 'source_language': 'auto', 'caption_language': 'en', 'video_type': 'auto'}
CHOICES = {'font': FONTS, 'theme': list(THEMES), 'format': list(FORMATS), 'framing': list(FRAMING), 'source_language': ['auto','en','ar','hi','ur','es','fr','de','ja','ko','zh','pt','ru'], 'caption_language': ['en','original'],'video_type':['auto','speech','lyrics','non-speech']}


def load_style(source_size: tuple[int, int] | None = None) -> dict:
    result = DEFAULTS.copy()
    if source_size:
        ratio = source_size[0] / source_size[1]
        if ratio < .72:
            result.update(format='9:16', framing='fit')
        elif ratio <= .9:
            result.update(format='4:5', framing='fit')
        elif ratio <= 1.12:
            result.update(format='1:1', framing='fit')
    path = home() / 'style.json'
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data,dict):
                result.update({key:value for key,value in data.items() if key in CHOICES and value in CHOICES[key]})
        except (ValueError, OSError):
            pass
    return result


def font_file(name: str) -> Path:
    return Path(__file__).parent / 'fonts' / FONT_FILES[name]


def color(ass_color: str) -> str:
    value=ass_color.removeprefix('&H')[-6:]
    return '#' + value[4:6] + value[2:4] + value[:2]


def load_font(name: str, size: int):
    """ASS uses bold captions; set variable fonts to a matching weight."""
    from PIL import ImageFont
    font=ImageFont.truetype(str(font_file(name)),size)
    try:
        axes=font.get_variation_axes()
        values=[min(axis['maximum'],max(axis['minimum'],700)) if b'weight' in axis['name'].lower() else axis['default'] for axis in axes]
        font.set_variation_by_axes(values)
    except (OSError,AttributeError):
        pass
    return font


def font_sample(name: str, width: int = 290, height: int = 66):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB',(width,height),'#171f30')
    draw = ImageDraw.Draw(image)
    size = 30
    while True:
        font = load_font(name,size)
        if draw.textlength('Make it count',font=font)<width-28 or size<=14:
            break
        size -= 1
    draw.text((width/2,height/2),'Make it count',font=font,fill='#f1f5fb',anchor='mm')
    return image


def preview(style: dict, width: int = 300, height: int = 460, source_frame=None):
    """Draw a representative still with the real bundled typeface."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
    outer = Image.new('RGB',(width,height),'#0b101b')
    fw,fh=FORMATS[style['format']]
    scale=min((width-24)/fw,(height-24)/fh)
    cw,ch=max(2,int(fw*scale)),max(2,int(fh*scale))
    scene=Image.new('RGB',(640,360),'#233e56')
    draw=ImageDraw.Draw(scene)
    for y in range(360):
        draw.line((0,y,640,y),fill=(29+int(y/15),62+int(y/10),82+int(y/14)))
    draw.rounded_rectangle((26,30,614,330),radius=18,outline='#5cb7ba',width=4)
    draw.rectangle((42,48,76,312),fill='#f7c969')
    draw.rectangle((564,48,598,312),fill='#f7c969')
    draw.ellipse((245,60,395,210),fill='#d3a27f')
    draw.rounded_rectangle((200,205,440,355),radius=35,fill='#8daac5')
    if source_frame is not None:
        scene = source_frame
    if style['framing']=='studio':
        region_width, region_height, center = studio_region(cw, ch)
        canvas = Image.new('RGB', (cw, ch), '#' + STUDIO_BACKGROUND)
        contained = ImageOps.contain(scene, (region_width, region_height))
        canvas.paste(contained, ((cw-contained.width)//2, center-contained.height//2))
    elif style['framing']=='face':
        canvas=ImageOps.fit(scene,(cw,ch))
    else:
        canvas=ImageOps.fit(scene,(cw,ch)).filter(ImageFilter.GaussianBlur(16)) if style['framing']=='blur' else Image.new('RGB',(cw,ch),'#10131c')
        contained=ImageOps.contain(scene,(cw,ch))
        canvas.paste(contained,((cw-contained.width)//2,(ch-contained.height)//2))
    draw=ImageDraw.Draw(canvas)
    theme=THEMES[style['theme']]
    size=max(10,int(cw*(.045 if theme.animation == 'steady' else .057)))
    words=['Make','it','count']
    while True:
        font=load_font(style['font'],size)
        lengths=[draw.textlength(word,font=font) for word in words]
        gap=draw.textlength(' ',font=font)
        total=sum(lengths)+gap*2
        if total<cw-20 or size<=9: break
        size-=1
    if style['framing'] == 'studio':
        y = round(ch * (1 - studio_caption_margin(cw, ch, scene.size)) - size / 2)
    else:
        y = int(ch * .5 if theme.alignment == 5 else ch * .85 - size / 2)
    x=(cw-total)/2
    stroke=max(1,round(theme.stroke*cw/1080))
    if theme.box:
        draw.rounded_rectangle((x-8,y-size*.8,x+total+8,y+size*.8),radius=3,fill='#050609')
    for index,word in enumerate(words):
        fill=color(theme.highlight if index==1 else theme.color)
        if theme.shadow:
            draw.text((x+2,y+2),word,font=font,fill='#040609',anchor='lm',stroke_width=stroke)
        draw.text((x,y),word,font=font,fill=fill,anchor='lm',stroke_width=stroke,stroke_fill=color(theme.outline_color))
        x+=lengths[index]+gap
    outer.paste(canvas,((width-cw)//2,(height-ch)//2))
    return outer


def contact_sheet(path: Path) -> Path:
    """Save an offline reference sheet for every font and theme."""
    from PIL import Image, ImageDraw, ImageFont
    image=Image.new('RGB',(1200,1380),'#0b101b')
    draw=ImageDraw.Draw(image)
    font=ImageFont.truetype(str(font_file('Inter')),18)
    heading=ImageFont.truetype(str(font_file('Inter')),30)
    draw.text((28,24),'CLIPFORGE / Visual templates',font=heading,fill='#eef4ff')
    draw.text((28,78),f'13 bundled fonts · {len(THEMES)} caption looks · full-picture layouts',font=font,fill='#aab7ce')
    for index,name in enumerate(FONTS):
        x=28+(index%4)*294; y=134+(index//4)*115
        draw.text((x,y),name,font=font,fill='#aab7ce')
        image.paste(font_sample(name,278,70),(x,y+27))
    for index,name in enumerate(THEMES):
        x=28+(index%4)*294; y=622+(index//4)*245
        draw.text((x,y),name,font=font,fill='#aab7ce')
        image.paste(preview({**DEFAULTS,'theme':name},278,205),(x,y+28))
    path.parent.mkdir(parents=True,exist_ok=True)
    image.save(path)
    return path


def choose_style(initial: dict | None = None, source: Path | None = None) -> dict | None:
    """Open a native visual picker and return selections directly to the CLI."""
    try:
        import tkinter as tk
        from tkinter import ttk
        from PIL import ImageTk
        root=tk.Tk()
    except (ImportError,RuntimeError) as exc:
        raise RuntimeError('Visual templates need Tkinter and Pillow. Use terminal menus or install Tk support (Linux: python3-tk).') from exc
    root.title('Clipforge · Visual templates')
    root.geometry(f'{min(1150,root.winfo_screenwidth()-60)}x{min(820,root.winfo_screenheight()-90)}')
    root.minsize(860,600)
    root.configure(bg='#0b101b')
    theme=ttk.Style(root); theme.theme_use('clam')
    theme.configure('TFrame',background='#0b101b')
    theme.configure('TLabel',background='#0b101b',foreground='#e8effc',font=('Segoe UI',10))
    theme.configure('TNotebook',background='#0b101b',borderwidth=0)
    theme.configure('TNotebook.Tab',background='#1d2a40',foreground='#eef4ff',padding=(18,10))
    theme.map('TNotebook.Tab',background=[('selected','#344c70')])
    style=load_style(); style.update({k:v for k,v in (initial or {}).items() if k in CHOICES and v in CHOICES[k]})
    source_frame = None
    if source is not None:
        import cv2
        from PIL import Image
        capture = cv2.VideoCapture(str(source))
        try:
            capture.set(cv2.CAP_PROP_POS_MSEC, 1000)
            ok, frame = capture.read()
            if ok:
                source_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                source_frame.thumbnail((960, 960))
        finally:
            capture.release()
    images=[]; cards={}; canvases={}; result=None
    header=tk.Frame(root,bg='#0b101b'); header.pack(fill='x',padx=24,pady=(16,10))
    tk.Label(header,text='Find your clip style',bg='#0b101b',fg='#f0f5ff',font=('Segoe UI',23,'bold')).pack(anchor='w')
    tk.Label(header,text='Click a template. See the actual fonts. Keep your full picture.',bg='#0b101b',fg='#aab7ce',font=('Segoe UI',11)).pack(anchor='w',pady=(5,0))
    body=ttk.Frame(root); body.pack(fill='both',expand=True,padx=24)
    left=ttk.Frame(body); left.pack(side='left',fill='y',padx=(0,22))
    preview_label=ttk.Label(left); preview_label.pack()
    detail=ttk.Label(left,text='',wraplength=290,justify='left'); detail.pack(anchor='w',pady=8)
    ttk.Label(left,text='Representative still; final captions animate.\nNo source image is cut in Fit modes.',wraplength=290,foreground='#8fa2bd').pack(anchor='w')
    notebook=ttk.Notebook(body); notebook.pack(side='left',fill='both',expand=True)

    def refresh():
        picture=ImageTk.PhotoImage(preview(style, source_frame=source_frame),master=root)
        preview_label.configure(image=picture); preview_label.image=picture
        detail.configure(text=f"{style['font']} / {style['theme']}\n{style['format']} / {FRAMING[style['framing']]}\nCaptions: {'English' if style['caption_language']=='en' else 'Original language'}\nSource: {style['source_language']} / {style['video_type']}")
        for (kind,value),card in cards.items():
            selected = all(style[key] == setting for key,setting in PRESETS[value].items()) if kind == 'preset' else style[kind] == value
            card.configure(highlightbackground='#68d8bf' if selected else '#24334c')

    def select(kind,value):
        if kind == 'preset':
            style.update(PRESETS[value])
        else:
            style[kind]=value
        refresh()

    def tab(title):
        page=ttk.Frame(notebook); notebook.add(page,text=title)
        canvas=tk.Canvas(page,bg='#0b101b',highlightthickness=0)
        scroll=ttk.Scrollbar(page,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvases[str(page)]=canvas
        scroll.pack(side='right',fill='y'); canvas.pack(side='left',fill='both',expand=True)
        content=ttk.Frame(canvas); canvas.create_window((0,0),window=content,anchor='nw')
        content.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        return content

    def card(parent,kind,value,picture,row,col,label=None):
        frame=tk.Frame(parent,bg='#171f30',highlightthickness=2,highlightbackground='#24334c',cursor='hand2')
        frame.grid(row=row,column=col,padx=6,pady=6,sticky='nsew'); cards[kind,value]=frame
        image=ImageTk.PhotoImage(picture,master=root); images.append(image)
        name=tk.Label(frame,text=label or value,bg='#171f30',fg='#e8effc',font=('Segoe UI',10,'bold'),wraplength=230)
        name.pack(pady=(10,2))
        sample=tk.Label(frame,image=image,bg='#171f30'); sample.pack(padx=5,pady=(2,5))
        for widget in (frame,name,sample): widget.bind('<Button-1>',lambda event,k=kind,v=value:select(k,v))

    presets=tab('Presets')
    for index,(name,preset) in enumerate(PRESETS.items()):
        label = f"{name.title()} · {preset['format']} · {FRAMING[preset['framing']]}"
        card(presets,'preset',name,preview({**style,**preset},240,205,source_frame),index//2,index%2,label)
    fonts=tab('Fonts')
    for index,name in enumerate(FONTS): card(fonts,'font',name,font_sample(name,240,65),index//2,index%2)
    looks=tab('Caption looks')
    for index,name in enumerate(THEMES): card(looks,'theme',name,preview({**style,'theme':name},240,205,source_frame),index//2,index%2)
    frames=tab('Framing & language')
    for index,value in enumerate(FRAMING): card(frames,'framing',value,preview({**style,'framing':value},240,210,source_frame),1+index//2,index%2,FRAMING[value])
    for index,value in enumerate(FORMATS): card(frames,'format',value,preview({**style,'format':value},240,210,source_frame),3+index//2,index%2,'Video shape '+value)
    controls=ttk.Frame(frames); controls.grid(row=0,column=0,columnspan=2,sticky='w',padx=12,pady=16)
    def combo(label,key,options):
        ttk.Label(controls,text=label).pack(anchor='w',pady=(8,3))
        variable=tk.StringVar(value=next(text for text,value in options if value==style[key]))
        widget=ttk.Combobox(controls,textvariable=variable,values=[text for text,value in options],state='readonly',width=43)
        widget.pack(anchor='w'); widget.bind('<<ComboboxSelected>>',lambda event:select(key,dict(options)[variable.get()]))
    combo('Caption language','caption_language',[('English (translate audio to English)','en'),('Keep original language','original')])
    combo('Language actually spoken / sung','source_language',list(zip(['Detect automatically','English','Arabic','Hindi','Urdu','Spanish','French','German','Japanese','Korean','Chinese','Portuguese','Russian'],CHOICES['source_language'])))
    combo('Audio content','video_type',[('Detect automatically','auto'),('Speech / podcast','speech'),('Lyrics / singing','lyrics'),('Visual narrative (not lyrics)','non-speech')])
    footer=tk.Frame(root,bg='#101827'); footer.pack(fill='x',side='bottom',pady=(12,0))
    def commit():
        nonlocal result
        result=style.copy()
        (home()/'style.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        root.destroy()
    tk.Label(footer,text='Selections go straight back to your terminal.',bg='#101827',fg='#aab7ce',font=('Segoe UI',10)).pack(side='left',padx=22,pady=18)
    tk.Button(footer,text='Use these settings  →',command=commit,bg='#68d8bf',fg='#071b19',activebackground='#95ead8',font=('Segoe UI',11,'bold'),relief='flat',padx=20,pady=9,cursor='hand2').pack(side='right',padx=20,pady=12)
    def wheel(event):
        canvas=canvases.get(notebook.select())
        if canvas is not None:
            delta=-1 if getattr(event,'num',None)==4 else 1 if getattr(event,'num',None)==5 else -int(event.delta/120)
            canvas.yview_scroll(delta,'units')
    root.bind_all('<MouseWheel>',wheel)
    root.bind_all('<Button-4>',wheel); root.bind_all('<Button-5>',wheel)
    root.bind('<Escape>',lambda event:root.destroy())
    refresh(); root.mainloop()
    return result

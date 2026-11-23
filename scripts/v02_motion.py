"""Charcoal Chapter Reveal, animated locally with Pillow and encoded by FFmpeg."""
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from graphics import font, charcoal
import render

W, H = 960, 540
ROMAN = ('I','II','III','IV')


def ease(t, start, end):
    x = min(1,max(0,(t-start)/(end-start)))
    return x*x*(3-2*x)


def blend_color(a,b,p):
    return tuple(round(x*(1-p)+y*p) for x,y in zip(a,b))


def draw_text(d,x,y,text,size,progress=1,serif=False,tone=(239,232,218),anchor=None):
    if progress <= .002:
        return
    face = font(render.CONFIG['fonts']['serif' if serif else 'sans'],size,not serif and size<20)
    d.text((x+round(15*(1-progress)),y),text,font=face,fill=blend_color((23,24,28),tone,progress),anchor=anchor)


def wrap(text, size, width):
    face=font(render.CONFIG['fonts']['sans'],size)
    lines=['']
    for word in text.split():
        line=(lines[-1]+' '+word).strip()
        if lines[-1] and face.getlength(line)>width:
            lines.append(word)
        else:
            lines[-1]=line
    return lines


@lru_cache
def grain():
    rng=np.random.default_rng(917)
    yy,xx=np.ogrid[-1:1:540j,-1:1:960j]
    shade=8*(1-xx*xx-yy*yy)+rng.normal(0,2.5,(H,W))
    return Image.fromarray(np.uint8(np.clip(np.array([20,22,26])+shade[:,:,None],0,255)))


def drawing(number):
    paths=[]
    steps=np.linspace(0,1,57)
    if number in (0,1):
        for k in range(23):
            if number==1:
                a=k*math.tau/23
                pts=[(712+math.cos(a+.10*x)*350*(1-x),261+math.sin(a+.10*x)*289*(1-x))
                     for x in steps]
            else:
                radius=300*.87**k
                pts=[(730+radius*(1+.07*math.sin(5*a+k*.28))*math.cos(a),
                      256+.85*radius*(1+.06*math.sin(5*a+k*.28))*math.sin(a))
                     for a in steps*math.tau]
            paths.append(pts)
    elif number==2:
        for x, side in ((604,-1),(790,1)):
            outline=[(-61,143),(-55,99),(-34,77),(-20,65),(-24,47),(-37,20),(-37,-20),
                     (-18,-46),(11,-47),(30,-29),(31,-5),(47,16),(32,23),(30,44),(16,56),
                     (15,68),(52,87),(72,115),(76,143)]
            for n in range(6):
                paths.append([(x+side*a+n*2,235+b+n*2) for a,b in outline])
        for n in range(15):
            x=690+n*1.5
            paths.append([(x+7*math.sin(z*7+n),121+z*272) for z in steps])
    elif number==3:
        for n in range(13):
            a=15+n*11
            x,y=728-a,267-a
            paths.append([(x+22,y),(x+2*a,y),(x+2*a,y+2*a),(x,y+2*a),(x,y+17)])
        paths += [[(588,160),(630,160),(630,180)],[(829,310),(795,310),(795,277),(776,277)],
                  [(713,406),(713,369),(687,369)]]
    elif number==4:
        for side in (-1,1):
            for page in range(8):
                paths.append([(710,335+page*2),(710+side*126,290+page*3),
                              (710+side*142,162+page*3),(710+side*92,172+page*3),(710,209+page*2)])
            for row in range(13):
                paths.append([(710+side*(11+126*x),224+row*7-(16+2*row)*math.sin(x*1.08))
                              for x in steps])
    return paths


@lru_cache
def paths_for(number):
    rng=np.random.default_rng(2026+number)
    styled=[]
    for i, points in enumerate(drawing(number)):
        for stroke in range(4):
            pts=np.array(points)+rng.normal(0,1.4+stroke*.65,(len(points),2))
            shade=50+stroke*9+int(rng.integers(0,8))
            color=(122,71,65) if i%8==0 and stroke==0 else (shade,shade+3,shade+6)
            styled.append((pts,color,1+(stroke==2)))
    return styled


def strokes(img,n,t,p):
    d=ImageDraw.Draw(img)
    offset=4*math.sin(t*.55)
    for i,(pts,col,w) in enumerate(paths_for(n)):
        stop=min(len(pts),round(len(pts)*(p*1.28-(i%17)*.012)))
        if stop<2:
            continue
        d.line([(x+offset*(1+i%3*.35),y+.7*offset) for x,y in pts[:stop]],fill=col,width=w)
    return d


def names(draw,t,p,y=285):
    config=render.CONFIG
    for i,person in enumerate(config['participants'].values()):
        x=109+(i%2)*406
        row=y+(i//2)*54
        draw_text(draw,x,row,person['name'],27,p,serif=True)
    draw_text(draw,109,y+124,config['class'],18,p)
    draw_text(draw,109,y+151,config['institution'],19,p)


def layout(row,t,portrait=None, thumbnail=False):
    config=render.CONFIG
    kind=row['card']
    duration=row['frames']/30
    number=row.get('number',0)
    image=grain().copy()
    p=ease(t,.32,2.05)
    d=strokes(image,number,t,p)
    ink=(182,96,79)
    if kind == 'open':
        if t<6.65 or thumbnail:
            reveal=1 if thumbnail else ease(t,.5,1.65)*(1-ease(t,5.93,6.62))
            draw_text(d,67,93,config['author'],23,reveal,tone=ink)
            draw_text(d,61,134,config['title'],86,reveal,serif=True)
            draw_text(d,67,250,config['subtitle'],26,reveal)
            draw_text(d,68,446,config['institution'],18,reveal)
        else:
            opacity=ease(t,6.64,7.33)
            draw_text(d,109,145,'INTEGRANTES',16,opacity,tone=ink)
            names(d,t,opacity,216)
    elif kind in ('chapter','bridge','bloopers'):
        title_progress=ease(t,1.65,2.66)
        description=ease(t,2.66,3.17)
        if portrait is not None:
            alpha=round(160*ease(t,.64,2))
            position=(543+round(12*(1-p)),135+round(math.sin(t*.75)*4))
            image.paste(portrait,position,Image.new('L',portrait.size,alpha))
            d=ImageDraw.Draw(image)
        kicker=f'CAPÍTULO {ROMAN[number-1]}' if number else ('BLOOPERS' if kind=='bloopers' else 'EPÍLOGO')
        d.rectangle((64,141,64+round(67*p),144),fill=ink)
        draw_text(d,64,159,kicker,17,title_progress,tone=ink)
        title=row['title']
        breaks={'La violencia empieza antes':('La violencia','empieza antes'),
                'La obsesión de poseer':('La obsesión','de poseer'),
                'Cuando el control parece amor':('Cuando el control','parece amor'),
                '¿Quién cuenta la historia?':('¿Quién cuenta','la historia?'),
                'Una pregunta que permanece':('Una pregunta','que permanece'),
                'DETRÁS DE CÁMARAS':('Detrás de cámaras',)}
        for i,line in enumerate(breaks[title]):
            draw_text(d,61,192+53*i,line,48,title_progress,serif=True)
        d.rectangle((64,323,64+round(69*description),324),fill=ink)
        for i,line in enumerate(wrap(row.get('deck',''),22,443)):
            draw_text(d,64,343+26*i,line,22,description)
    else:
        q=ease(t,.55,1.55)
        draw_text(d,109,91,config['title'],58,q,serif=True)
        if kind=='end':
            draw_text(d,112,176,'Gracias por acompañarnos',33,q)
        else:
            draw_text(d,112,176,config['subtitle'],27,q)
        names(d,t,ease(t,1.37,2.1),246)
        fade=ease(t,duration-1.2,duration-.25) if kind=='end' else 0
        if fade:
            image=Image.blend(image,Image.new('RGB',(W,H),(15,16,19)),fade)
    return image


@lru_cache
def mask_texture():
    rng=np.random.default_rng(88)
    low=np.uint8(rng.integers(0,255,(56,100)))
    texture=Image.fromarray(low).resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1))
    return np.asarray(texture,dtype=np.float32)/255


def wipe(previous, following, t):
    level=np.clip((t-mask_texture()*.25-.08)*7,0,1)
    mask=Image.fromarray(np.uint8(level*255))
    return Image.composite(following,previous,mask)


def still(ref,path):
    if not ref:
        return None
    render.ff('-v','error','-ss',ref[1],'-i',render.source({'clip':ref[0]}),
              '-frames:v',1,'-vf','scale=960:540:flags=lanczos','-threads',1,path)
    with Image.open(path) as img:
        return img.convert('RGB')


def music(path,row):
    duration=row['frames']/30
    rate=48000
    t=np.arange(row['frames']*1600)/rate
    left=np.zeros_like(t)
    right=np.zeros_like(t)
    happy=row['card']=='bloopers'
    interval=.20 if happy else .31
    for base in ([.18,7.15] if row['card']=='open' else [.18]):
        for i,note in enumerate((261.63,329.63,392.,293.66) if happy else (146.83,220.,261.63,196.)):
            age=np.maximum(0,t-(base+i*interval))
            env=(1-np.exp(-age/.024))*np.exp(-age/.62)
            sin=np.sin(math.tau*note*age + .24*np.sin(math.tau*note*2*age))
            tick=.09*np.sin(math.tau*note*3*age)*np.exp(-age/.067)
            left+=.124*env*(sin+tick)
            right+=.124*env*(np.sin(math.tau*note*age+.15)+tick)
    amp=np.minimum(1,t/.10)*np.minimum(1,(duration-t)/.72)
    with wave.open(str(path),'wb') as out:
        out.setparams((2,2,rate,0,'NONE','not compressed'))
        out.writeframes(np.int16(np.stack((left*amp,right*amp),axis=1)*32767).tobytes())


def motion(row,rows):
    del rows
    directory=render.OUT/'recursos'/row['id']
    directory.mkdir(parents=True,exist_ok=True)
    encoded=render.WORK/f'{row["id"]}.mov'
    stamp=directory/'render.sha256'
    key=hashlib.sha256((json.dumps([row,render.CONFIG['participants'],render.CONFIG['institution'],
                                   render.CONFIG['class'],render.CONFIG['title'],render.CONFIG['author'],
                                   render.CONFIG['subtitle']],sort_keys=True)
                        +Path(__file__).read_text()).encode()).hexdigest()
    if encoded.exists() and stamp.exists() and stamp.read_text()==key:
        return encoded
    previous=still(row.get('prev'),render.WORK/f'{row["id"]}-prev.jpg')
    following=still(row.get('next'),render.WORK/f'{row["id"]}-next.jpg')
    portrait=still(row.get('portrait'),render.WORK/f'{row["id"]}-portrait.jpg')
    if portrait is not None:
        portrait=charcoal(portrait,render.CONFIG).resize((357,259),Image.Resampling.LANCZOS)
    music(directory/'motivo.wav',row)
    layout(row,4,portrait).save(directory/'arte.png')
    if row['card']=='open':
        layout(row,3,thumbnail=True).resize((1280,720),Image.Resampling.LANCZOS).save(directory/'thumbnail.jpg',quality=94)
    cmd=['ffmpeg','-v','error','-nostdin','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','960x540',
         '-framerate','30','-i','pipe:0','-i',str(directory/'motivo.wav'),'-filter_threads','2',
         '-vf','scale=1920:1080:flags=lanczos:out_range=limited,format=yuv420p,setsar=1',
         *render.VIDEO,'-ar','48000','-c:a','pcm_s16le','-video_track_timescale','30000',str(encoded)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as task:
        for frame in range(row['frames']):
            t=frame/30
            art=layout(row,t,portrait)
            if previous is not None and t<.64:
                art=wipe(previous,art,t/.64)
            remaining=(row['frames']-1-frame)/30
            if following is not None and remaining<.63:
                art=wipe(following,art,remaining/.63)
            task.stdin.write(art.tobytes())
        task.stdin.close()
        if task.wait():
            raise RuntimeError(f'Falló la cortina {row["id"]}')
    stamp.write_text(key)
    print(row['id'],row['frames'],flush=True)
    return encoded

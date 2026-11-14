"""Narration-first editorial 2D renderer. Python + Pillow + FFmpeg."""
import argparse, hashlib, json, math, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def run(args):
    subprocess.run([str(x) for x in args], check=True)

def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)]))

def validate(project):
    scenes = project.get('scenes', [])
    if not 1 <= len(scenes) <= 60:
        raise ValueError('Provide 1–60 scenes')
    for s in scenes:
        if s.get('layout') not in ('room','cards','pitch','outro'):
            raise ValueError('Unknown 2D layout')
        if not isinstance(s.get('narration'), str) or not s['narration'].strip():
            raise ValueError('Every scene needs narration')
        if len(s['narration']) > 600:
            raise ValueError('Split narration into shorter scenes')
        if not isinstance(s.get('title',''), str):
            raise ValueError('Scene title must be text')
    return scenes

def voice(scene, project, folder, base, silent):
    if silent:
        seconds = max(2, len(scene['narration'].split()) / 2.6)
        path = folder / (hashlib.sha256(scene['narration'].encode()).hexdigest() + '.wav')
        run(['ffmpeg','-v','error','-y','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',seconds,path])
    elif scene.get('voice_file'):
        path = (base / scene['voice_file']).resolve()
        if not path.is_file(): raise ValueError(f'Missing narration: {path}')
    else:
        name = project.get('voice','es-ES-AlvaroNeural')
        digest = hashlib.sha256((name + scene['narration']).encode()).hexdigest()
        path = folder / (digest + '.mp3')
        if not path.exists():
            tmp = folder / (digest + '.pending.mp3')
            try:
                subprocess.run([sys.executable,'-m','edge_tts','--voice',name,'--text',scene['narration'],'--write-media',str(tmp)], check=True, timeout=90)
                if duration(tmp) <= 0: raise ValueError('Empty narration')
                tmp.replace(path)
            except (subprocess.SubprocessError, ValueError) as exc:
                tmp.unlink(missing_ok=True)
                raise RuntimeError('Voice generation failed. Install edge-tts and enable network, or provide voice_file for every scene. No silent production export was made.') from exc
    seconds = duration(path)
    if not 0 < seconds <= 90: raise ValueError('Narration must last 0–90 seconds per scene')
    return path, seconds + .35

class Canvas:
    def __init__(self, width):
        self.w = width; self.h = width * 16 // 9; self.s = width / 540
        self.im = Image.new('RGB',(self.w,self.h)); self.d = ImageDraw.Draw(self.im)
    def box(self, xy, fill, radius=0, outline=None, stroke=1):
        self.d.rounded_rectangle(tuple(round(v*self.s) for v in xy),radius=round(radius*self.s),fill=fill,outline=outline,width=max(1,round(stroke*self.s)))
    def ellipse(self, xy, fill):
        self.d.ellipse(tuple(round(v*self.s) for v in xy),fill=fill)
    def line(self, xy, fill, width=2):
        self.d.line(tuple(round(v*self.s) for v in xy),fill=fill,width=max(1,round(width*self.s)))
    def text(self, xy, text, size=24, color='#F5EBDD', bold=False, anchor='mm'):
        font=ImageFont.truetype(BOLD if bold else FONT,max(1,round(size*self.s)))
        self.d.text(tuple(round(v*self.s) for v in xy),text,font=font,fill=color,anchor=anchor)
    def wrap(self, text, size, limit=450):
        font=ImageFont.truetype(BOLD,max(1,round(size*self.s)))
        lines=[]; line=''
        for word in text.split():
            attempt=(line+' '+word).strip()
            if font.getlength(attempt)>limit*self.s and line: lines.append(line); line=word
            else: line=attempt
        if line: lines.append(line)
        return lines

def character(c,x,y,t,talking=False):
    bob=math.sin(t*3)*2
    y+=bob
    skin='#DFA276'
    c.ellipse((x-54,y+175,x+54,y+193),'#151C2A')
    for dx in (-23,23):
        c.line((x+dx,y+109,x+dx,y+176),'#283B54',22)
        c.box((x+dx-14,y+171,x+dx+20,y+184),'#F3E8D3',5)
    c.box((x-47,y+20,x+47,y+112),'#587AE1',16)
    c.box((x-38,y+27,x+36,y+38),'#7197FF',5)
    c.line((x-43,y+39,x-69,y+91),skin,17)
    c.line((x+43,y+39,x+72,y+27-math.sin(t*3)*16),skin,17)
    c.ellipse((x-33,y-49,x+33,y+28),skin)
    c.box((x-35,y-52,x+32,y-20),'#302724',14)
    for dx in (-12,12):
        c.ellipse((x+dx-3,y-10,x+dx+3,y-3),'#26262A')
    mouth=3+abs(math.sin(t*18))*7 if talking else 3
    c.ellipse((x-8,y+9,x+8,y+9+mouth),'#653F3F')

def frame(scene,t,total,width,index,count):
    c=Canvas(width)
    for y in range(c.h):
        p=y/c.h; c.d.line((0,y,c.w,y),fill=(int(22+17*p),int(32+12*p),int(52+18*p)))
    c.text((42,56),'UNIFORMER / STUDIO',15,'#92AEC8',True,'lm')
    c.text((497,56),f'{index+1:02d} / {count:02d}',14,'#92AEC8',anchor='rm')
    title=c.wrap(scene.get('title',''),38)
    for i,line in enumerate(title[:3]): c.text((270,128+i*47),line,38,bold=True)
    ease=1-(1-min(1,t/.65))**3; dy=(1-ease)*65
    layout=scene['layout']
    if layout=='room':
        c.box((24,300,516,728),'#324957',18)
        c.box((44,324,233,500),'#203747',8, '#658190',2)
        for x in range(60,225,25):
            c.box((x,348+(x%3)*9,x+14,438),'#C79964' if x%2 else '#70978E',2)
        c.line((46,448,232,448),'#748D92',7)
        c.ellipse((405,325,474,394),'#DBD7C3')
        c.line((440,359,440,336),'#314652',3); c.line((440,359,459,367),'#314652',3)
        character(c,285,451+dy,t,True)
        c.box((65,614,475,635),'#C49A73',6)
        c.box((85,635,105,728),'#715744',3); c.box((435,635,455,728),'#715744',3)
        c.box((207,543,358,618),'#111F32',8,'#8BA5B6',2)
        c.text((282,577),'UniFormer',19,bold=True)
    elif layout=='cards':
        labels=scene.get('cards',['Elige tu equipo','Decide la táctica','Juega tu partido'])
        for i,label in enumerate(labels[:3]):
            y=310+i*118+max(0,dy-i*10)
            c.box((48,y+8,492,y+102),'#111B2A',14)
            c.box((42,y,486,y+94),'#EEE5D4',14)
            c.ellipse((61,y+23,107,y+69),'#DF8A51')
            c.text((84,y+46),str(i+1),21,'#FFFFFF',True)
            for j,line in enumerate(c.wrap(label,22,330)[:2]): c.text((125,y+35+j*27),line,22,'#293B4B',True,'lm')
        character(c,430,696,t,True)
    elif layout=='pitch':
        c.box((40,296,500,716),'#467E73',16)
        for y in range(316,700,64): c.box((42,y,498,y+30),'#4B8679')
        c.box((62,319,478,691),'#467E73',2,'#BBD6B9',3)
        c.line((62,504,478,504),'#BBD6B9',3)
        c.d.ellipse(tuple(round(v*c.s) for v in (215,449,325,559)),outline='#BBD6B9',width=max(1,round(3*c.s)))
        for k,(x,y) in enumerate([(140,370),(340,402),(200,570),(392,632),(265,332)]):
            x+=math.sin(t*1.8+k)*12
            c.ellipse((x-19,y-19,x+19,y+19),'#EABB65' if k%2 else '#648AF1')
            c.text((x,y),str(k+7),16,bold=True)
        bx=210+100*math.sin(t*1.3); by=540-95*math.sin(t*.9)
        c.ellipse((bx-9,by-9,bx+9,by+9),'#FFF3D9')
        c.box((140,738,400,788),'#EABB65',12)
        c.text((270,763),'TU PRÓXIMA JUGADA',19,'#203448',True)
    else:
        c.ellipse((137,300+dy,403,566+dy),'#354E6C')
        c.text((270,434+dy),'U',145,'#F0C576',True)
        c.text((270,610),'UniFormer',42,bold=True)
        for j,line in enumerate(c.wrap(scene.get('cta','El partido empieza contigo.'),25)):
            c.text((270,684+j*33),line,25,'#E9C173',True)
    words=scene['narration'].split(); chunks=[' '.join(words[i:i+5]) for i in range(0,len(words),5)]
    cue=min(len(chunks)-1,int(t/max(.01,total-.35)*len(chunks)))
    lines=c.wrap(chunks[cue],27,440)
    c.box((32,825,508,850+len(lines)*34),'#101B2B',12)
    for j,line in enumerate(lines): c.text((270,848+j*34),line,27,bold=True)
    c.box((40,934,500,938),'#43536B',2)
    c.box((40,934,40+max(1,460*t/total),938),'#F0C576',2)
    return c.im

def main():
    p=argparse.ArgumentParser(); p.add_argument('--project',required=True,type=Path); p.add_argument('--output',required=True,type=Path)
    p.add_argument('--width',type=int,default=1080); p.add_argument('--fps',type=int,default=30)
    p.add_argument('--silent-preview',action='store_true'); a=p.parse_args()
    if a.width not in (270,540,1080) or not 12<=a.fps<=60: p.error('width: 270/540/1080; fps: 12–60')
    project=json.loads(a.project.read_text()); scenes=validate(project)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    cache=a.output.parent/'voice_cache'; cache.mkdir(exist_ok=True)
    narration=[voice(s,project,cache,a.project.parent,a.silent_preview) for s in scenes]
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp); clips=[]; offset=0; cues=[]
        for i,(s,(sound,seconds)) in enumerate(zip(scenes,narration)):
            frames=math.ceil(seconds*a.fps); seconds=frames/a.fps
            clip=tmp/f'{i:03d}.mp4'; clips.append(clip)
            cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{a.width}x{a.width*16//9}','-r',str(a.fps),'-i','pipe:0','-i',str(sound),'-af','apad,loudnorm=I=-16:TP=-1.5:LRA=9','-t',str(seconds),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-ar','48000',str(clip)]
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
            try:
                for f in range(frames): proc.stdin.write(frame(s,f/a.fps,seconds,a.width,i,len(scenes)).tobytes())
            finally:
                proc.stdin.close(); result=proc.wait()
            if result: raise RuntimeError('FFmpeg render failed')
            cues.append({'start':offset,'end':offset+seconds,'text':s['narration']}); offset+=seconds
        listing=tmp/'concat.txt'; listing.write_text('\n'.join("file '"+str(c)+"'" for c in clips))
        pending=tmp/'final.mp4'
        run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',listing,'-c','copy','-movflags','+faststart',pending])
        import shutil
        shutil.copyfile(pending,a.output)
    a.output.with_suffix('.json').write_text(json.dumps({'duration':offset,'voice':not a.silent_preview,'caption_timing':'estimated phrase timing; not forced alignment','scenes':cues},ensure_ascii=False,indent=2))
    print(a.output)

if __name__=='__main__': main()

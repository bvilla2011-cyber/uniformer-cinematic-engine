"""UniFormer Studio: deterministic procedural 2.5D short-film engine.

Scenes are selected from a small trusted registry. A creative brief can change
copy, pacing and palette but cannot inject Python code or shell commands.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_W, BASE_H = 540, 960
SCENE_TYPES = {"rooftop", "forge", "reveal"}
MAX_DURATION = 60


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def smooth(v):
    v = clamp(v)
    return v * v * (3 - 2 * v)


def validate_project(data):
    if not isinstance(data, dict):
        raise ValueError("Project must be a JSON object")
    if not isinstance(data.get("title"), str) or len(data["title"]) > 100:
        raise ValueError("title must be a string <= 100 characters")
    shots = data.get("shots")
    if not isinstance(shots, list) or not 1 <= len(shots) <= 12:
        raise ValueError("shots must contain between 1 and 12 entries")
    duration = 0.0
    for i, shot in enumerate(shots):
        if not isinstance(shot, dict) or shot.get("type") not in SCENE_TYPES:
            raise ValueError(f"shots[{i}] has an unknown scene type")
        seconds = shot.get("duration")
        if not isinstance(seconds, (int, float)) or not 0.5 <= seconds <= 15:
            raise ValueError(f"shots[{i}].duration must be 0.5..15 seconds")
        duration += seconds
        for field in ("headline", "subtitle"):
            if not isinstance(shot.get(field, ""), str) or len(shot.get(field, "")) > 70:
                raise ValueError(f"shots[{i}].{field} must be <= 70 characters")
    if duration > MAX_DURATION:
        raise ValueError("Project exceeds 60 seconds")
    captions = data.get("captions", [])
    if not isinstance(captions, list) or len(captions) > 150:
        raise ValueError("captions must be a list of at most 150 items")
    for item in captions:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) or len(item["text"]) > 80:
            raise ValueError("Invalid caption text")
        start, end = item.get("start"), item.get("end")
        if (not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                or not math.isfinite(start) or not math.isfinite(end)
                or not 0 <= start < end <= duration):
            raise ValueError("Invalid caption timing")
    return duration


def get_font(size, bold=True):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


class Studio:
    def __init__(self, project, width=BASE_W, height=BASE_H, logo_path=None):
        self.project = project
        self.duration = validate_project(project)
        self.width, self.height = width, height
        self.scale = width / BASE_W
        if height != round(BASE_H * self.scale):
            raise ValueError("Only 9:16 dimensions are supported")
        self.starts = np.cumsum([0] + [s["duration"] for s in project["shots"]]).tolist()
        self.gradients = {}
        self.glows = {}
        self.logo = None
        if logo_path:
            self.logo = Image.open(logo_path).convert("RGBA")
            self.logo.thumbnail(self.pt(210, 210), Image.Resampling.LANCZOS)

    def font(self, n, bold=True):
        return get_font(max(8, round(n*self.scale)), bold)

    def pt(self, x, y):
        return round(x*self.scale), round(y*self.scale)

    def gradient(self, top, bottom):
        key = (top, bottom)
        if key not in self.gradients:
            rows = np.linspace(0, 1, self.height, dtype=np.float32)[:, None, None]
            a = np.array(top, dtype=np.float32).reshape(1, 1, 3)
            b = np.array(bottom, dtype=np.float32).reshape(1, 1, 3)
            pixels = np.repeat((a*(1-rows)+b*rows).astype(np.uint8), self.width, axis=1)
            self.gradients[key] = Image.fromarray(pixels, "RGB").convert("RGBA")
        return self.gradients[key].copy()

    def poly(self, d, points, fill, outline=None, width=1):
        d.polygon([self.pt(*p) for p in points], fill=fill)
        if outline:
            d.line([self.pt(*p) for p in points+[points[0]]], fill=outline, width=max(1,round(width*self.scale)), joint="curve")

    def line(self, d, points, fill, width=1):
        d.line([self.pt(*p) for p in points], fill=fill, width=max(1,round(width*self.scale)), joint="curve")

    def ellipse(self, d, bounds, fill, outline=None, width=1):
        d.ellipse((*self.pt(*bounds[:2]), *self.pt(*bounds[2:])), fill=fill, outline=outline, width=max(1,round(width*self.scale)))

    def glow(self, im, x, y, radius=100, color=(54, 210, 255), strength=180):
        key = (radius, color, strength, self.scale)
        if key not in self.glows:
            r = max(2, round(radius*self.scale))
            sprite = Image.new("RGBA", (2*r, 2*r))
            p = ImageDraw.Draw(sprite)
            p.ellipse((r*.43,r*.43,r*1.57,r*1.57), fill=(*color, strength))
            sprite = sprite.filter(ImageFilter.GaussianBlur(r*.35))
            self.glows[key] = sprite
        sprite = self.glows[key]
        x, y = self.pt(x, y)
        im.alpha_composite(sprite, (x-sprite.width//2, y-sprite.height//2)) if 0 <= x-sprite.width//2 and 0 <= y-sprite.height//2 and x+sprite.width//2 <= self.width and y+sprite.height//2 <= self.height else self._paste_glow(im, sprite, x, y)

    @staticmethod
    def _paste_glow(im, sprite, x, y):
        # Cropped alpha composite supports glows near the canvas edges.
        left, top = x-sprite.width//2, y-sprite.height//2
        box = (max(0,left),max(0,top),min(im.width,left+sprite.width),min(im.height,top+sprite.height))
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        part = sprite.crop((box[0]-left,box[1]-top,box[2]-left,box[3]-top))
        im.alpha_composite(part, box[:2])

    def stars(self, d, t, count=65, drift=8):
        for i in range(count):
            z = .25+(i%11)/11
            x = (i*137.57 + t*drift*z) % 540
            y = (i*83.31 + t*4*z) % 680
            r = .65+(i%3)*.45
            self.ellipse(d,(x-r,y-r,x+r,y+r),(91,170,220,round(45+120*z)))

    def city(self, d, t, shift=0):
        for layer in (0, 1, 2):
            base = 646+layer*45
            speed = (layer+1)*7
            color = [(18,34,59,255),(15,28,52,255),(10,20,38,255)][layer]
            for i in range(14):
                x = (i*53-30 - t*speed + shift*(layer+1)) % 660 - 60
                w = 28 + (i*13+layer*17)%50
                h = 70 + (i*37+layer*47)%170
                self.poly(d,[(x,base),(x,base-h),(x+w,base-h),(x+w,base)],color)
                if layer < 2:
                    for j in range(3):
                        yy = base-h+18+j*24
                        if yy < base-10 and (i+j)%3 != 0:
                            self.poly(d,[(x+9,yy),(x+13,yy),(x+13,yy+7),(x+9,yy+7)],(49,161,204,125))

    def actor(self, d, t, x=270, y=700, scale=1, facing=1):
        bob = math.sin(t*2.6)*3
        s = scale
        def p(px,py): return (x+facing*px*s,y+py*s+bob)
        # Shadow, legs, coat, articulated arm, head, hair and visor.
        self.ellipse(d,(x-48*s,y+70*s,x+49*s,y+84*s),(0,0,0,90))
        self.line(d,[p(-16,15),p(-22,71)],(14,22,37,255),13*s)
        self.line(d,[p(16,15),p(23,71)],(14,22,37,255),13*s)
        self.poly(d,[p(-38,-88),p(32,-90),p(46,24),p(-45,24)],(27,53,84,255))
        self.poly(d,[p(-30,-83),p(-5,-89),p(1,22),p(-35,20)],(40,78,110,255))
        self.poly(d,[p(12,-82),p(30,-84),p(42,18),p(22,20)],(19,40,66,255))
        # Right arm moves to present a spark.
        lift = smooth((t-1.0)/1.0)
        elbow = p(42,-42-12*lift)
        hand = p(56+25*lift,-20-70*lift)
        self.line(d,[p(27,-75),elbow,hand],(30,68,103,255),16*s)
        self.ellipse(d,(hand[0]-8*s,hand[1]-8*s,hand[0]+8*s,hand[1]+8*s),(211,182,148,255))
        self.ellipse(d,(x-26*s,y-143*s+bob,x+26*s,y-89*s+bob),(191,154,126,255))
        self.poly(d,[p(-29,-128),p(-22,-152),p(13,-155),p(29,-137),p(13,-143),p(-12,-140)],(10,25,45,255))
        self.poly(d,[p(-23,-120),p(20,-123),p(19,-110),p(-20,-107)],(33,183,229,230))
        return hand

    def title(self, im, headline, subtitle, opacity=1):
        d = ImageDraw.Draw(im,"RGBA")
        alpha = round(255*clamp(opacity))
        if not alpha:
            return
        x, y = self.pt(270, 94)
        if headline:
            d.text((x,y),headline.upper(),font=self.font(34),anchor="mt",fill=(239,248,255,alpha),stroke_width=round(self.scale))
        if subtitle:
            d.text(self.pt(270,143),subtitle.upper(),font=self.font(16),anchor="mt",fill=(106,219,246,alpha))

    def scene_rooftop(self, t, dur, shot):
        im=self.gradient((4,9,25),(31,62,94))
        d=ImageDraw.Draw(im,"RGBA")
        self.stars(d,t)
        # Crescent, antenna, city and cinematic camera drift.
        self.glow(im,420,190,105,(50,132,210),135)
        d=ImageDraw.Draw(im,"RGBA")
        self.ellipse(d,(365,140,477,252),(113,170,215,160))
        self.ellipse(d,(388,128,493,232),(8,19,41,255))
        self.city(d,t,shift=math.sin(t*.35)*12)
        self.poly(d,[(0,755),(540,745),(540,960),(0,960)],(10,19,35,255))
        self.poly(d,[(0,760),(540,750),(540,770),(0,781)],(36,65,92,255))
        for i in range(11):
            x= i*55-18
            self.line(d,[(x,770),(x-48,960)],(32,63,93,100),2)
        hand=self.actor(d,t,260,710,1.25)
        power=smooth((t-1.1)/1.5)
        self.glow(im,hand[0],hand[1],45+power*50,(60,219,252),round(70+power*150))
        d=ImageDraw.Draw(im,"RGBA")
        self.ellipse(d,(hand[0]-7,hand[1]-7,hand[0]+7,hand[1]+7),(192,250,255,round(100+155*power)))
        for i in range(14):
            a=i*2.4+t*2
            r=14+power*(16+i%5*9)
            x=hand[0]+math.cos(a)*r
            y=hand[1]+math.sin(a)*r
            self.ellipse(d,(x-2,y-2,x+2,y+2),(104,229,255,round(180*power)))
        self.title(im,shot.get("headline",""),shot.get("subtitle",""),smooth(t/.5))
        return im

    def scene_forge(self,t,dur,shot):
        im=self.gradient((2,8,23),(14,31,58))
        d=ImageDraw.Draw(im,"RGBA")
        self.stars(d,t,90,25)
        cx=270+math.sin(t*1.1)*6
        cy=475
        # Floor, horizon and a rotating ring of distinct low-poly parts.
        self.poly(d,[(0,680),(540,680),(540,960),(0,960)],(8,23,42,255))
        for i in range(-7,8):
            self.line(d,[(cx,680),(cx+i*110,960)],(34,115,163,130),2)
        for k in range(1,10):
            z=((k/10+t*.2)%1)
            yy=680+z*z*280
            self.line(d,[(0,yy),(540,yy)],(38,123,165,round(35+100*z)),2)
        growth=smooth((t-.25)/1.5)
        self.glow(im,cx,cy,185,(21,160,237),round(110*growth))
        d=ImageDraw.Draw(im,"RGBA")
        self.ellipse(d,(cx-38,cy-38,cx+38,cy+38),(17,64,112,255),outline=(102,227,255,255),width=4)
        self.ellipse(d,(cx-13,cy-13,cx+13,cy+13),(206,249,255,255))
        for i in range(16):
            a=(i/16)*math.tau + t*(.4 if i%2 else -.3)
            rad=(90+(i%3)*42)*growth
            x=cx+math.cos(a)*rad
            y=cy+math.sin(a)*rad*.72
            size=(8+i%4*4)*growth
            self.poly(d,[(x,y-size),(x+size,y+size*.6),(x-size,y+size)],
                      [(38,154,211,210),(48,214,229,235),(98,137,218,200)][i%3],
                      outline=(170,243,255,140))
        for i in range(6):
            a=t*1.4+i*math.tau/6
            x=cx+math.cos(a)*115*growth
            y=cy+math.sin(a)*65*growth
            self.ellipse(d,(x-3,y-3,x+3,y+3),(217,251,255,240))
        # Beam appears progressively; not a static card.
        beam=smooth((t-1.1)/1.2)
        self.poly(d,[(cx-18*beam,cy),(cx+18*beam,cy),(cx+55*beam,80),(cx-55*beam,80)],(57,192,240,round(28*beam)))
        self.title(im,shot.get("headline",""),shot.get("subtitle",""),smooth(t/.45))
        return im

    def scene_reveal(self,t,dur,shot):
        im=self.gradient((3,16,40),(38,98,130))
        d=ImageDraw.Draw(im,"RGBA")
        self.stars(d,t,30,4)
        rise=smooth((t-.15)/1.9)
        self.glow(im,270,390,210,(61,197,245),round(130*rise))
        d=ImageDraw.Draw(im,"RGBA")
        # Floating island built from separate planes, not a single bitmap.
        y=580+int((1-rise)*230)
        self.poly(d,[(40,y),(268,y-100),(500,y),(265,y+140)],(14,44,75,255))
        self.poly(d,[(40,y),(265,y+140),(230,y+220),(100,y+95)],(14,32,59,255))
        self.poly(d,[(265,y+140),(500,y),(425,y+110),(230,y+220)],(8,24,46,255))
        self.poly(d,[(40,y),(268,y-100),(500,y),(265,y+140)],(40,131,151,255),outline=(103,236,232,255),width=3)
        # Emerging stylized towers with layered depth and animated windows.
        for i in range(10):
            x=105+i*33
            h=(70+(i*31)%115)*smooth((t-.2-i*.1)/1.0)
            top=y-42-(i%3)*14
            self.poly(d,[(x,top),(x+20,top-9),(x+20,top-h-9),(x,top-h)],(18,52+5*(i%4),80+4*(i%4),255))
            self.poly(d,[(x+20,top-9),(x+29,top-3),(x+29,top-h-3),(x+20,top-h-9)],(8,36,65,255))
            self.poly(d,[(x,top-h),(x+20,top-h-9),(x+29,top-h-3),(x+9,top-h+7)],(57,177,192,255))
            for j in range(3):
                wy=top-h+22+j*18
                if wy<top-8:
                    self.poly(d,[(x+6,wy),(x+11,wy-2),(x+11,wy+5),(x+6,wy+7)],(81,228,243,160))
        # Aerial drones with arcs.
        for i in range(3):
            x=70+i*145+math.sin(t*(1.1+i*.3))*40
            yy=315+i*55+math.sin(t*2+i)*13
            self.poly(d,[(x-13,yy),(x,yy-6),(x+13,yy),(x,yy+6)],(215,242,245,235))
            self.ellipse(d,(x-3,yy-3,x+3,yy+3),(48,217,249,255))
        # Wordmark stays over animated world. Use official logo via optional overlay later.
        self.title(im,shot.get("headline",""),shot.get("subtitle",""),smooth((t-.45)/.5))
        return im

    def render_at(self,t):
        t=max(0,min(t,self.duration-1e-6))
        i=int(np.searchsorted(self.starts,t,side="right")-1)
        i=min(i,len(self.project["shots"])-1)
        shot=self.project["shots"][i]
        local=t-self.starts[i]
        methods={"rooftop":self.scene_rooftop,"forge":self.scene_forge,"reveal":self.scene_reveal}
        im=methods[shot["type"]](local,shot["duration"],shot)
        # A short light-driven dissolve prevents hard scene cuts.
        if i+1<len(self.project["shots"]) and local>shot["duration"]-.30:
            a=smooth((local-(shot["duration"]-.30))/.30)
            nextshot=self.project["shots"][i+1]
            other=methods[nextshot["type"]](0,nextshot["duration"],nextshot)
            im=Image.blend(im,other,a)
        if self.logo is not None and i == len(self.project["shots"]) - 1:
            alpha = smooth((local - .7) / .65)
            if alpha:
                logo = self.logo.copy()
                logo.putalpha(logo.getchannel("A").point(lambda v: round(v * alpha)))
                im.alpha_composite(logo, (round((self.width - logo.width) / 2), self.pt(0, 620)[1]))
        for caption in self.project.get("captions", []):
            if caption["start"] <= t < caption["end"]:
                d = ImageDraw.Draw(im, "RGBA")
                caption_font = self.font(27)
                txt = caption["text"].upper()
                box = d.textbbox((0, 0), txt, font=caption_font)
                tw = box[2] - box[0]
                x, y = self.pt(270, 847)
                pad = round(17 * self.scale)
                d.rounded_rectangle((x-tw/2-pad, y-pad, x+tw/2+pad, y+round(43*self.scale)),
                                    radius=round(12*self.scale), fill=(4, 14, 30, 205))
                d.text((x, y), txt, font=caption_font, anchor="mt", fill=(255, 255, 255, 255))
                break
        return im.convert("RGB")


def synthesize_audio(seconds, shots, dest, sr=24000):
    """Original synthesized music and sound cues, not copyrighted samples."""
    n=int(seconds*sr)
    t=np.arange(n,dtype=np.float64)/sr
    mix=np.zeros(n,dtype=np.float64)
    chord=[110,146.83,164.81,196]
    for j,f in enumerate(chord):
        mix += (.038/(1+j*.5))*np.sin(2*np.pi*f*t + .1*np.sin(t*.5))
    mix*=np.minimum(1,t/.5)*np.minimum(1,(seconds-t)/.6)
    for beat in np.arange(0,seconds,.50):
        start=int(beat*sr); count=min(int(.22*sr),n-start)
        idx=np.arange(count)/sr
        mix[start:start+count]+=.13*np.sin(2*np.pi*(80*idx-140*idx**2))*np.exp(-idx*29)
    elapsed=0
    for shot in shots:
        start=int((elapsed+.25)*sr)
        count=min(int(.75*sr),n-start)
        if count>0:
            idx=np.arange(count)/sr
            f=330 if shot["type"]=="rooftop" else 440 if shot["type"]=="forge" else 550
            mix[start:start+count]+=.09*np.sin(2*np.pi*(f*idx+80*idx*idx))*np.exp(-idx*4)
        elapsed+=shot["duration"]
    pcm=np.int16(np.clip(mix,-.95,.95)*32767)
    with wave.open(str(dest),"wb") as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(sr);out.writeframes(pcm.tobytes())


def ffprobe(path):
    out=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height", "-of","json",str(path)],capture_output=True,text=True,check=True)
    return json.loads(out.stdout)


def render(project_path,output, fps=24, width=540, preview=False, voiceover=None, logo=None):
    data=json.loads(Path(project_path).read_text(encoding="utf-8"))
    height=round(width*16/9)
    studio=Studio(data,width,height,logo_path=logo)
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe must be installed")
    duration=studio.duration
    count=round(duration*fps)
    if preview:
        count=min(count,48)
        duration=count/fps
    cover_t=min(studio.duration-.01,float(data.get("cover_at",studio.duration*.75)))
    cover=output.with_name(output.stem+"_cover.png")
    studio.render_at(cover_t).save(cover)
    sheet=Image.new("RGB",(width*len(data["shots"]),height))
    for i,shot in enumerate(data["shots"]):
        im=studio.render_at(studio.starts[i]+shot["duration"]*.55)
        sheet.paste(im,(i*width,0))
    storyboard=output.with_name(output.stem+"_storyboard.jpg")
    sheet.save(storyboard,quality=84)
    with tempfile.TemporaryDirectory() as tmp:
        audio=Path(tmp)/"score.wav"
        synthesize_audio(duration,data["shots"],audio)
        command=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{width}x{height}","-r",str(fps),"-i","pipe:0","-i",str(audio)]
        if voiceover:
            command += ["-i",str(voiceover),"-filter_complex","[1:a]volume=0.45[m];[m][2:a]amix=inputs=2:duration=first:dropout_transition=0[a]","-map","0:v:0","-map","[a]"]
        command += ["-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart","-t",str(duration),str(output)]
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for i in range(count):
                process.stdin.write(studio.render_at(i/fps).tobytes())
            process.stdin.close()
            error=process.stderr.read().decode("utf-8",errors="replace")
            code=process.wait()
        except Exception:
            process.kill();process.wait();raise
        if code:
            raise RuntimeError("ffmpeg failed: "+error[-3000:])
    probe=ffprobe(output)
    streams=probe.get("streams",[])
    assert any(s.get("codec_type")=="video" for s in streams)
    assert any(s.get("codec_type")=="audio" for s in streams)
    assert output.stat().st_size>20000
    report={"status":"pass","project":data["title"],"duration":float(probe["format"]["duration"]),"frames":count,"resolution":f"{width}x{height}","audio":True,"video":str(output.name),"cover":cover.name,"storyboard":storyboard.name,"size_bytes":output.stat().st_size,"preview":preview}
    report_path=output.with_name(output.stem+"_report.json")
    report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser(description="UniFormer Cinematic Engine")
    p.add_argument("--project",default="projects/first_light.json")
    p.add_argument("--output",default="output/first_light.mp4")
    p.add_argument("--width",type=int,default=540,choices=[270,540,720,1080])
    p.add_argument("--fps",type=int,default=24,choices=[12,24,30])
    p.add_argument("--preview",action="store_true")
    p.add_argument("--voiceover",type=Path)
    p.add_argument("--logo",type=Path,help="Optional official logo PNG with transparency")
    args=p.parse_args()
    print(json.dumps(render(args.project,args.output,args.fps,args.width,args.preview,args.voiceover,args.logo),indent=2))


if __name__=="__main__":
    main()

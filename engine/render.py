"""Procedural 2.5D motion-graphics prototype for UniFormer Studio.

Produces independent animated objects, parallax, camera shake, light effects
and original procedural sound. No remote AI dependency is needed for rendering.
"""
import argparse
import math
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 540, 960
FPS = 24
DURATION = 8
BG = (8, 13, 30)


def font(size):
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if os.path.exists(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def glow(im, x, y, radius, color):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for r in range(radius, 0, -8):
        a = int(45 * (1 - r / (radius + 1)))
        d.ellipse((x-r, y-r, x+r, y+r), fill=(*color, a))
    im.alpha_composite(layer)


def frame(t):
    im = Image.new("RGBA", (W, H), (*BG, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Deep-space background with independent parallax particles.
    for i in range(105):
        depth = 0.25 + (i % 9) / 9
        x = int((i * 173.2 + t * 11 * depth) % W)
        y = int((i * 89.7 + t * 31 * depth) % H)
        r = 1 + i % 3
        d.ellipse((x-r,y-r,x+r,y+r), fill=(80, 160, 230, 45 + int(100*depth)))
    # Perspective floor with moving vanishing point.
    horizon = 630
    cx = W//2 + int(18*math.sin(t*.6))
    d.polygon([(0,horizon),(W,horizon),(W,H),(0,H)], fill=(14,25,52,255))
    for i in range(-7, 8):
        d.line((cx,horizon,cx+i*105,H),fill=(30,126,194,100),width=2)
    for k in range(1, 10):
        z = ((k/10 + t*.28)%1)
        y = int(horizon + (z*z)*(H-horizon))
        d.line((0,y,W,y), fill=(30,126,194, int(30+120*z)), width=2)
    # Glowing planet, with orbital ring.
    px = cx + int(34*math.sin(t*.4))
    py = 310 + int(16*math.sin(t*.8))
    glow(im,px,py,180,(19,135,236))
    d = ImageDraw.Draw(im,"RGBA")
    d.ellipse((px-102,py-102,px+102,py+102),fill=(19,81,145,255),outline=(99,214,255,255),width=4)
    d.arc((px-147,py-46,px+147,py+46),0,360,fill=(112,227,255,200),width=5)
    d.polygon([(px-95,py-24),(px-20,py-78),(px+30,py-48),(px+8,py+10)],fill=(44,129,184,130))
    # A spacecraft with rotation and independent engine pulse.
    sx = 90 + int(360*min(1,t/6))
    sy = 520 + int(60*math.sin(t*1.1))
    pulse = 15 + int(13*(1+math.sin(t*15))/2)
    d.polygon([(sx-48,sy),(sx-100-pulse,sy+22),(sx-65,sy+5)],fill=(255,117,51,210))
    d.polygon([(sx-45,sy-18),(sx+45,sy),(sx-45,sy+18),(sx-20,sy)],fill=(201,225,238,255))
    d.ellipse((sx-10,sy-9,sx+10,sy+9),fill=(30,185,255,255))
    # Editorial motion typography.
    headline = "THE NEXT WORLD"
    sub = "IS YOURS TO CREATE"
    alpha = min(255,max(0,int((t-.3)*360)))
    if t < 5.8:
        d.text((W//2,75),headline,font=font(37),anchor="mt",fill=(245,249,255,alpha),stroke_width=1)
        d.text((W//2,127),sub,font=font(22),anchor="mt",fill=(72,207,255,alpha))
    else:
        fade = min(255,int((t-5.8)*360))
        d.rounded_rectangle((55,65,W-55,180),radius=16,fill=(8,18,40,min(220,fade)))
        d.text((W//2,94),"UNIFORMER",font=font(52),anchor="mt",fill=(245,249,255,fade))
        d.text((W//2,153),"STUDIO",font=font(23),anchor="mt",fill=(70,206,255,fade))
    d.text((W//2,890),"ORIGINAL WORLDS. INFINITE STORIES.",font=font(16),anchor="mt",fill=(172,200,220,230))
    return im.convert("RGB")


def make_audio(path):
    sr = 22050
    n = sr*DURATION
    a = np.zeros(n,dtype=np.float64)
    for start, freq in [(0,110),(2,164.81),(4,196),(6,130.81)]:
        idx = np.arange(sr*2)
        env = np.minimum(1,idx/(sr*.15))*np.minimum(1,(sr*2-idx)/(sr*.4))
        chord = .12*np.sin(2*np.pi*freq*idx/sr)+.045*np.sin(2*np.pi*freq*1.5*idx/sr)
        a[start*sr:(start+2)*sr] += chord*env
    # Soft synthetic beat.
    for beat in np.arange(0,DURATION,.5):
        start=int(beat*sr)
        count=min(int(.15*sr),n-start)
        idx=np.arange(count)
        a[start:start+count] += .17*np.sin(2*np.pi*(90-60*idx/count)*idx/sr)*np.exp(-idx/(sr*.035))
    pcm=np.int16(np.clip(a,-1,1)*32767)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="output/uniformer_teaser.mp4")
    p.add_argument("--frames",type=int,default=FPS*DURATION)
    args=p.parse_args()
    if not shutil.which("ffmpeg"):
        raise SystemExit("Install ffmpeg to render MP4")
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        tmp=Path(temp)
        for i in range(args.frames):
            frame(i/FPS).save(tmp/f"f_{i:05d}.png")
        make_audio(tmp/"score.wav")
        subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),
            "-i",str(tmp/"f_%05d.png"),"-i",str(tmp/"score.wav"),
            "-c:v","libx264","-preset","fast","-pix_fmt","yuv420p",
            "-c:a","aac","-shortest","-movflags","+faststart",str(output)],check=True)
    print(f"Rendered {output}")


if __name__=="__main__":
    main()

"""Product-first 2D advertisement: real gameplay, authorized logo, voice and SFX."""
import argparse, math, subprocess, tempfile, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from studio import voice, duration

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def main():
 p=argparse.ArgumentParser();p.add_argument('--gameplay',type=Path,required=True);p.add_argument('--logo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--width',type=int,default=1080);a=p.parse_args()
 if a.width not in (540,1080):p.error('width must be 540 or 1080')
 if not a.gameplay.is_file() or not a.logo.is_file():p.error('A real gameplay recording and authorized logo are required')
 a.output.parent.mkdir(parents=True,exist_ok=True);cache=a.output.parent/'voice_cache';cache.mkdir(exist_ok=True)
 script='Tu club. Tu historia. Construye tu equipo. Dirige desde el banquillo. Y vive cada partido. Super Soccer. De UniFormer Studio.'
 audio,spoken=voice({'narration':script},{'voice':'es-ES-AlvaroNeural'},cache,Path.cwd(),False)
 total=max(15,spoken+1);fps=30;frames=math.ceil(total*fps);total=frames/fps;w=a.width;h=w*16//9;s=w/540
 logo=Image.open(a.logo).convert('RGBA');logo=logo.crop(logo.getbbox());logo.thumbnail((int(315*s),int(240*s)),Image.Resampling.LANCZOS)
 def font(n):return ImageFont.truetype(FONT,round(n*s))
 with tempfile.TemporaryDirectory() as tmp:
  tmp=Path(tmp);raw=tmp/'visual.mp4'
  reader=subprocess.Popen(['ffmpeg','-v','error','-stream_loop','-1','-i',str(a.gameplay),'-vf','scale=960:600,fps=30','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
  writer=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r','30','-i','pipe:0','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',str(raw)],stdin=subprocess.PIPE)
  end=total-3.0
  def box(d,xy,fill,r=0,outline=None):d.rounded_rectangle(tuple(round(v*s) for v in xy),radius=round(r*s),fill=fill,outline=outline,width=max(1,round(s)))
  def txt(d,x,y,text,size,color='#F2E9CE',anchor='mm'):d.text((x*s,y*s),text,font=font(size),fill=color,anchor=anchor)
  for k in range(frames):
   t=k/fps;data=reader.stdout.read(960*600*3)
   if len(data)!=960*600*3:raise RuntimeError('Gameplay decode failed')
   game=Image.frombytes('RGB',(960,600),data)
   im=Image.new('RGB',(w,h),'#10282E');d=ImageDraw.Draw(im)
   # Fine architectural grid and the actual game palette.
   for x in range(0,w,round(45*s)):d.line((x,0,x,h),fill='#17353A')
   for y in range(0,h,round(45*s)):d.line((0,y,w,y),fill='#17353A')
   txt(d,35,49,'UNIFORMER STUDIO',12,'#B6C6AE','lm');txt(d,505,49,'SUPER / SOCCER',12,'#D4EB86','rm')
   if t<end:
    phase=min(2,int(t/end*3));start=phase*end/3;u=t-start;ease=1-(1-min(1,u/.55))**4
    titles=[('TU CLUB.','TU HISTORIA.'),('EL PARTIDO','SE DIRIGE.'),('CADA JUGADA','CUENTA.')]
    for j,line in enumerate(titles[phase]):txt(d,32+(1-ease)*55,140+j*60,line,44,'#F2E9CE' if j==0 else '#D4EB86','lm')
    # Show the whole genuine field: no fake controls or made-up game statistics.
    box(d,(18,286,522,657),'#071C22',12,'#4C6961')
    shot=game.resize((round(500*s),round(312.5*s)),Image.Resampling.LANCZOS)
    im.paste(shot,(round(20*s),round(323*s)));d=ImageDraw.Draw(im)
    txt(d,34,306,'PARTIDA REAL · SIMULACIÓN DEL JUEGO',11,'#AFC1AC','lm')
    box(d,(32,681,508,756),'#1C3C3D',9,'#4C6961')
    labels=['CONSTRUYE TU EQUIPO','DIRIGE DESDE EL BANQUILLO','VIVE CADA PARTIDO']
    txt(d,58,718,f'0{phase+1}',22,'#D4EB86','lm');txt(d,107,718,labels[phase],18,'#F2E9CE','lm')
    for j in range(3):box(d,(32+j*161,780,181+j*161,784),'#D4EB86' if j<=phase else '#36534E',2)
    txt(d,270,856,'SUPER SOCCER',36)
    txt(d,270,899,'TU CLUB. TU HISTORIA.',14,'#B6C6AE')
   else:
    u=t-end;ease=1-(1-min(1,u/.65))**3
    im.paste(logo,(int((w-logo.width)/2),round((260+35*(1-ease))*s)),logo);d=ImageDraw.Draw(im)
    txt(d,270,592,'SUPER SOCCER',39)
    txt(d,270,647,'TU CLUB. TU HISTORIA.',18,'#D4EB86')
    box(d,(95,738,445,802),'#D4EB86',8);txt(d,270,770,'DESCUBRE EL JUEGO',19,'#10282E')
   writer.stdin.write(im.tobytes())
  writer.stdin.close();code=writer.wait();reader.stdout.close();reader.terminate();reader.wait()
  if code:raise RuntimeError('Video encoding failed')
  # Original audio accents. These mark editorial cuts, not fictitious in-game events.
  rate=48000;rng=np.random.default_rng(42);sound=np.zeros(round(total*rate),dtype=np.float64)
  for when in [0,end/3,2*end/3,end]:
   n=int(.42*rate);x=np.arange(n)/rate;env=np.sin(np.pi*np.arange(n)/n)**2
   swoosh=rng.standard_normal(n)*env*.035 + np.sin(2*np.pi*(130*x-85*x*x))*np.exp(-x*12)*.14
   i=int(when*rate);take=min(n,len(sound)-i);sound[i:i+take]+=swoosh[:take]
   i+=int(.12*rate);n=int(.065*rate);x=np.arange(n)/rate;click=np.sin(2*np.pi*1050*x)*np.exp(-x*85)*.10;take=min(n,len(sound)-i);sound[i:i+take]+=click[:take]
  bedtime=np.arange(len(sound))/rate
  sound+=.018*np.sin(2*np.pi*110*bedtime)*(np.sin(2*np.pi*.8*bedtime)**8)
  sound*=np.minimum(1,(total-bedtime)/.5)
  effects=tmp/'effects.wav'
  with wave.open(str(effects),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((np.clip(sound,-1,1)*32767).astype('<i2').tobytes())
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-i',str(audio),'-i',str(effects),'-filter_complex','[1:a]apad,loudnorm=I=-16:TP=-2:LRA=8[v];[v][2:a]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.89[a]','-map','0:v','-map','[a]','-t',str(total),'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(a.output)],check=True)
 print(a.output)
if __name__=='__main__':main()

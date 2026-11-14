"""Narration-led Super Soccer campaign edit with cinematic 2D shot composition."""
import argparse, json, math, subprocess, tempfile, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from studio import voice

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CREAM='#F2E9CE'; LIME='#D4EB86'; INK='#10282E'

def main():
 p=argparse.ArgumentParser();p.add_argument('--gameplay',type=Path,required=True);p.add_argument('--logo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--width',type=int,default=1080);a=p.parse_args()
 if a.width not in (540,1080):p.error('width must be 540 or 1080')
 if not a.gameplay.is_file() or not a.logo.is_file():p.error('Actual gameplay and authorized logo are required')
 w=a.width;h=w*16//9;s=w/540;fps=30;a.output.parent.mkdir(parents=True,exist_ok=True)
 cache=a.output.parent/'voice_cache';cache.mkdir(exist_ok=True)
 scenes=[('hook','Aquí, el partido también se juega desde el banquillo.'),('team','Tu equipo. Tus decisiones.'),('action','Sigue la jugada. Vive cada partido.'),('hero','Super Soccer. Tu club. Tu historia.'),('brand','De UniFormer Studio.')]
 voices=[voice({'narration':text},{'voice':'es-ES-AlvaroNeural'},cache,Path.cwd(),False) for _,text in scenes]
 lengths=[math.ceil((max(d,2.1)+.3)*fps)/fps for _,d in voices];starts=np.cumsum([0]+lengths[:-1]).tolist();total=sum(lengths)
 fonts={}
 def font(n):
  key=round(n*s)
  if key not in fonts:fonts[key]=ImageFont.truetype(FONT,key)
  return fonts[key]
 def ease(v):return 1-(1-min(1,max(0,v)))**4
 def text(im,x,y,t,size,color=CREAM,anchor='lm'):
  ImageDraw.Draw(im).text((x*s,y*s),t,font=font(size),fill=color,anchor=anchor)
 def box(im,xy,fill,r=0,outline=None):ImageDraw.Draw(im).rounded_rectangle(tuple(round(v*s) for v in xy),radius=round(r*s),fill=fill,outline=outline,width=max(1,round(s)))
 def line(im,xy,fill,width=1):ImageDraw.Draw(im).line(tuple(round(v*s) for v in xy),fill=fill,width=max(1,round(width*s)))
 # Precompute a subtle radial studio background and readable footage vignette.
 yy,xx=np.mgrid[0:h,0:w];light=np.exp(-(((xx/w-.72)/.65)**2+((yy/h-.35)/.6)**2)*2)
 bg=np.zeros((h,w,3),dtype=np.uint8)
 for ch,(base,amount) in enumerate([(9,16),(28,25),(34,25)]):bg[:,:,ch]=base+light*amount
 background=Image.fromarray(bg)
 alpha=(np.maximum(0,(.38-yy/h)/.38)*225+np.maximum(0,(yy/h-.58)/.42)*245).clip(0,248).astype('uint8')
 shade=Image.new('RGBA',(w,h),(5,22,28));shade.putalpha(Image.fromarray(alpha))
 logo=Image.open(a.logo).convert('RGBA');logo=logo.crop(logo.getbbox());logo.thumbnail((round(300*s),round(225*s)),Image.Resampling.LANCZOS)
 with tempfile.TemporaryDirectory() as folder:
  tmp=Path(folder)
  # Render at the game's own aspect; the edit applies purposeful portrait crops.
  reader=subprocess.Popen(['ffmpeg','-v','quiet','-stream_loop','-1','-i',str(a.gameplay),'-vf','scale=960:600,fps=30','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
  raw=tmp/'picture.mp4';writer=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r','30','-i','pipe:0','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',str(raw)],stdin=subprocess.PIPE)
  frames=round(total*fps)
  for k in range(frames):
   t=k/fps;i=max(j for j,start in enumerate(starts) if t>=start);local=t-starts[i];progress=local/lengths[i];kind=scenes[i][0]
   data=reader.stdout.read(960*600*3)
   if len(data)!=960*600*3:raise RuntimeError('Gameplay decoding ended unexpectedly')
   game=Image.frombytes('RGB',(960,600),data);im=background.copy()
   if kind in ('hook','action','hero'):
    # Continuous close-up, then a wide context inset in the action beat.
    cx=480+math.sin(t*.22)*105;cw=420-30*ease(progress);cy=300
    crop=game.crop((int(cx-cw/2),int(cy-300),int(cx+cw/2),int(cy+300)))
    im=ImageOps.fit(crop,(w,h),method=Image.Resampling.LANCZOS).convert('RGBA');im.alpha_composite(shade);im=im.convert('RGB')
   if kind=='hook':
    text(im,32,132,'EL PARTIDO',48)
    text(im,32,190+24*(1-ease(local/.6)),'TAMBIÉN SE',43)
    text(im,32,246+24*(1-ease((local-.12)/.6)),'DIRIGE.',64,LIME)
    if local>1.6:
     box(im,(30,708,510,820),INK,8,'#476861');text(im,52,748,'DESDE EL',20);text(im,52,788,'BANQUILLO.',35,LIME)
   elif kind=='team':
    # A layered, moving match window; headline remains the primary reading target.
    text(im,32,146,'TU EQUIPO.',53);text(im,32,208,'TUS DECISIONES.',35,LIME)
    lift=45*(1-ease(local/.6));box(im,(22,300+lift,518,659+lift),'#061A20',10,'#557970')
    shot=game.resize((round(480*s),round(300*s)),Image.Resampling.LANCZOS);im.paste(shot,(round(30*s),round((342+lift)*s)))
    text(im,42,321+lift,'SUPER SOCCER / SEÑAL DEL ESTADIO',11,'#AFC3B4')
    for j,label in enumerate(['CONSTRUYE','DIRIGE','COMPITE']):
     reveal=ease((local-.2-j*.12)/.4);x=30+j*165
     box(im,(x,714+30*(1-reveal),x+150,778+30*(1-reveal)),LIME if j==1 else '#1A3B3C',5)
     text(im,x+75,746+30*(1-reveal),label,14,INK if j==1 else CREAM,'mm')
    text(im,32,862,'LA HISTORIA EMPIEZA CONTIGO.',15,'#B3C5B6')
   elif kind=='action':
    text(im,32,133,'SIGUE',64);text(im,32,202,'LA JUGADA.',52,LIME)
    # Wide original view preserves context beside the close-up crop.
    shot=game.resize((round(230*s),round(144*s)),Image.Resampling.LANCZOS)
    box(im,(278,672,516,850),INK,6,'#658275');im.paste(shot,(round(282*s),round(701*s)));text(im,288,687,'VISTA COMPLETA',10)
    text(im,32,752,'VIVE',36);text(im,32,797,'CADA',36);text(im,32,842,'PARTIDO.',32,LIME)
   elif kind=='hero':
    # Oversized title locks up over the game, one line at a time.
    box(im,(0,298,540,657),'#10282E',0)
    text(im,28,385,'SUPER',88)
    text(im,28+38*(1-ease((local-.15)/.6)),487,'SOCCER',78,LIME)
    line(im,(32,550,508,550),'#65816E')
    text(im,270,594,'TU CLUB. TU HISTORIA.',23,CREAM,'mm')
   else:
    # Use exactly the supplied transparent brand asset.
    scale=.94+.06*ease(local/.7);mark=logo.resize((round(logo.width*scale),round(logo.height*scale)),Image.Resampling.LANCZOS)
    im.paste(mark,((w-mark.width)//2,round(285*s)),mark)
    text(im,270,593,'SUPER SOCCER',37,CREAM,'mm');text(im,270,638,'TU CLUB. TU HISTORIA.',17,LIME,'mm')
    box(im,(100,731,440,794),LIME,5);text(im,270,762,'DESCUBRE EL JUEGO',18,INK,'mm')
   text(im,30,49,'UNIFORMER STUDIO',11,'#CAD7C2');text(im,510,49,'SUPER / SOCCER',11,LIME,'rm')
   line(im,(30,77,510,77),'#678373')
   # Short opaque wipe gives cuts a designed transition without hiding gameplay for long.
   if i>0 and local<.3:
    q=local/.3;left=int((-1+2*q)*w);ImageDraw.Draw(im).polygon([(left,0),(left+w,0),(left+w-int(.15*w),h),(left-int(.15*w),h)],fill=LIME)
   writer.stdin.write(im.tobytes())
  writer.stdin.close();result=writer.wait();reader.stdout.close();reader.terminate();reader.wait()
  if result:raise RuntimeError('Picture encoding failed')
  # Segment narration for exact phrase-level scene boundaries, padding only pauses.
  pieces=[]
  for i,((src,_),length) in enumerate(zip(voices,lengths)):
   dest=tmp/f'voice{i}.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-af','apad','-t',str(length),'-ar','48000','-ac','1',str(dest)],check=True);pieces.append(dest)
  listing=tmp/'audio.txt';listing.write_text('\n'.join("file '"+str(x)+"'" for x in pieces))
  narration=tmp/'narration.wav';subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),str(narration)],check=True)
  rate=48000;sample=np.arange(round(total*rate))/rate;music=np.zeros(len(sample));fx=np.zeros(len(sample));rng=np.random.default_rng(7)
  # Original restrained arpeggio and a bass pulse; narration ducks the bed below it.
  for beat in np.arange(0,total,.375):
   note=[220,261.63,329.63,392,329.63,261.63,196,261.63][round(beat/.375)%8];n=min(round(.55*rate),len(sample)-round(beat*rate));x=np.arange(n)/rate
   tone=(np.sin(2*np.pi*note*x)+.25*np.sin(2*np.pi*note*2*x))*np.exp(-x*9)*.032
   start=round(beat*rate);music[start:start+n]+=tone
  for when in starts:
   start=round(when*rate);n=min(round(.45*rate),len(sample)-start);x=np.arange(n)/rate;env=np.sin(np.pi*np.arange(n)/n)**2
   noise=rng.standard_normal(n);noise=np.convolve(noise,np.ones(12)/12,mode='same')
   fx[start:start+n]+=noise*env*.12+np.sin(2*np.pi*(92*x-45*x*x))*np.exp(-x*17)*.2
  for when in [starts[1]+.32,starts[1]+.48,starts[1]+.64]:
   start=round(when*rate);n=round(.08*rate);x=np.arange(n)/rate;fx[start:start+n]+=np.sin(2*np.pi*950*x)*np.exp(-x*60)*.045
  fade=np.minimum(1,np.maximum(0,(total-sample)/.65));music*=fade;fx*=fade
  for name,data in [('music',music),('effects',fx)]:
   with wave.open(str(tmp/f'{name}.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((np.clip(data,-1,1)*32767).astype('<i2').tobytes())
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-i',str(narration),'-i',str(tmp/'music.wav'),'-i',str(tmp/'effects.wav'),'-filter_complex','[1:a]loudnorm=I=-16:TP=-2:LRA=8,asplit=2[v][side];[2:a][side]sidechaincompress=threshold=0.025:ratio=5:attack=15:release=220[m];[v][m][3:a]amix=inputs=3:duration=longest:normalize=0,alimiter=limit=0.79:level=false[a]','-map','0:v','-map','[a]','-t',str(total),'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(a.output)],check=True)
 a.output.with_suffix('.timing.json').write_text(json.dumps({'duration':total,'scenes':[{'start':st,'duration':d,'layout':kind,'narration':txt} for st,d,(kind,txt) in zip(starts,lengths,scenes)]},ensure_ascii=False,indent=2))
 print(a.output)
if __name__=='__main__':main()

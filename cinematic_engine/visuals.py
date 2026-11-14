"""Original procedural 2.5D soccer cinematics; real continuous motion at every frame."""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TEAL=(53,225,212)
GOLD=(255,194,90)
WHITE=(241,251,255)
TWO_PI=math.tau

def ease(x):
    x=max(0,min(1,x))
    return x*x*(3-2*x)

def between(a,b,t): return a+(b-a)*t

class Stage:
    def __init__(self,w,h):
        self.w,self.h=w,h
        self.sx,self.sy=w/720,h/1280
        self.scale=min(self.sx,self.sy)
        self.fonts={}
        self.backgrounds={}
        x=np.linspace(-1,1,w,dtype=np.float32)[None,:,None]
        y=np.linspace(0,1,h,dtype=np.float32)[:,None,None]
        for name,top,bottom in (
            ("tunnel",(5,10,26),(16,43,70)),
            ("pitch",(8,21,42),(14,62,70)),
            ("goal",(6,17,33),(22,68,82)),
            ("brand",(5,9,25),(20,39,64))):
            arr=(np.asarray(top)[None,None,:]*(1-y)+np.asarray(bottom)[None,None,:]*y)
            arr=arr*(.79+.21*(1-np.abs(x)))
            self.backgrounds[name]=Image.fromarray(np.broadcast_to(arr,(h,w,3)).astype(np.uint8).copy(),"RGB")
    def p(self,x,y): return (round(x*self.sx),round(y*self.sy))
    def bounds(self,x0,y0,x1,y1):return (*self.p(x0,y0),*self.p(x1,y1))
    def begin(self,name):
        self.im=self.backgrounds[name].convert("RGBA")
        self.d=ImageDraw.Draw(self.im)
    def poly(self,points,color):self.d.polygon([self.p(*xy) for xy in points],fill=color)
    def line(self,points,color,width=3):
        self.d.line([self.p(*xy) for xy in points],fill=color,width=max(1,round(width*self.scale)),joint="curve")
    def ell(self,x0,y0,x1,y1,color): self.d.ellipse(self.bounds(x0,y0,x1,y1),fill=color)
    def rect(self,x0,y0,x1,y1,fill,radius=6,outline=None):
        self.d.rounded_rectangle(self.bounds(x0,y0,x1,y1),radius=max(1,round(radius*self.scale)),fill=fill,outline=outline,width=max(1,round(self.scale*2)))
    def txt(self,string,y,size=42,color=WHITE):
        size=max(8,round(size*self.scale))
        if size not in self.fonts:
            try:self.fonts[size]=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",size)
            except OSError:self.fonts[size]=ImageFont.load_default()
        self.d.text(self.p(360,y),string,font=self.fonts[size],anchor="mt",fill=color,stroke_width=max(1,round(2*self.scale)),stroke_fill=(7,15,34))
    def glow(self,cx,cy,rx,ry,color,strength=95):
        layer=Image.new("RGBA",(self.w,self.h))
        ImageDraw.Draw(layer).ellipse(self.bounds(cx-rx,cy-ry,cx+rx,cy+ry),fill=(*color,strength))
        self.im=Image.alpha_composite(self.im,layer.filter(ImageFilter.GaussianBlur(max(2,round(min(rx*self.sx,ry*self.sy)*.36)))))
        self.d=ImageDraw.Draw(self.im)
    def dust(self,sec,n=65):
        rng=np.random.default_rng(817)
        for x,y,depth in rng.random((n,3)):
            xx=x*720+math.sin(sec*2+y*10)*16*depth
            yy=170+((y+sec*(.035+.12*depth))%1)*940
            r=1+depth*2
            self.ell(xx-r,yy-r,xx+r,yy+r,(*TEAL,round(40+100*depth)))

    def actor(self,x,y,scale,phase,jersey,facing=1,dark=False):
        swing=math.sin(TWO_PI*phase)
        skin=(227,177,134) if not dark else (22,40,55)
        shorts=(15,35,56)
        self.ell(x-45*scale,y-11*scale,x+47*scale,y+11*scale,(2,13,24,150))
        for side in (-1,1):
            hip=(x+side*12*scale,y-94*scale)
            knee=(hip[0]+side*swing*24*scale,y-48*scale)
            foot=(knee[0]+(side*swing+facing*.55)*22*scale,y-5*scale)
            self.line([hip,knee,foot],shorts,15*scale)
            self.line([foot,(foot[0]+facing*9*scale,foot[1])],(229,247,243),10*scale)
        self.poly([(x-32*scale,y-178*scale),(x+31*scale,y-178*scale),
                   (x+27*scale,y-94*scale),(x-27*scale,y-94*scale)],jersey)
        self.rect(x-27*scale,y-111*scale,x+26*scale,y-87*scale,shorts,3)
        for side in (-1,1):
            hand=(x+side*(42+17*swing*side)*scale,y-99*scale)
            self.line([(x+side*30*scale,y-162*scale),(x+side*47*scale,y-121*scale),hand],skin,11*scale)
        self.rect(x-10*scale,y-192*scale,x+9*scale,y-167*scale,skin,5)
        self.ell(x-25*scale,y-242*scale,x+25*scale,y-185*scale,skin)
        self.poly([(x-25*scale,y-224*scale),(x-18*scale,y-244*scale),
                   (x+9*scale,y-248*scale),(x+27*scale,y-230*scale),
                   (x+24*scale,y-219*scale),(x,y-229*scale)],(13,24,35))
        if not dark:
            self.ell(x+(facing*9-2)*scale,y-209*scale,x+(facing*9+2)*scale,y-204*scale,(14,25,37))
    def tunnel(self,t,length):
        self.begin("tunnel")
        self.glow(360,469,248,269,TEAL,115)
        self.poly([(0,0),(720,0),(472,445),(246,445)],(18,36,61))
        self.poly([(0,0),(246,445),(165,958),(0,1280)],(16,36,61))
        self.poly([(720,0),(472,445),(552,958),(720,1280)],(11,30,56))
        self.poly([(246,445),(472,445),(545,953),(165,953)],(30,105,108))
        self.poly([(0,1280),(165,953),(545,953),(720,1280)],(8,27,44))
        for side in (-1,1):
            self.line([(360+side*239,454),(360+side*353,1280)],(*TEAL,180),6)
            for i in range(5):
                yy=72+i*172
                xx=360+side*(198+i*27)
                self.line([(xx,yy),(xx+side*51,yy+149)],(*TEAL,105),4)
        for i in range(8):
            yy=964+i*i*5
            self.line([(0,yy),(720,yy)],(56,160,167,80),2)
        self.actor(360+math.sin(t*2)*12,965-142*ease(t/length),1.02,t*2.1,(16,42,58),dark=True)
    def pitch(self,t,length):
        self.begin("pitch")
        self.ell(-153,101,870,862,(8,36,56))
        self.ell(-100,172,829,830,(26,75,87))
        self.ell(-67,199,796,793,(7,26,44))
        rng=np.random.default_rng(37)
        for i in range(380):
            a=rng.uniform(0,TWO_PI)
            r=rng.uniform(320,440)
            x=360+r*math.cos(a)
            y=480+r*.57*math.sin(a)
            if 215<y<787:
                color=(TEAL,GOLD,(129,187,210),(47,122,148))[i%4]
                self.ell(x,y,x+4,y+4,(*color,175))
        self.glow(550,244,184,114,TEAL,95)
        self.poly([(-140,735),(785,677),(905,1199),(-184,1262)],(9,94,83))
        for i in range(8):
            y=750+i*66
            self.line([(-110,y+30),(810,y-24)],(20,128,107,100),34)
        self.line([(-124,767),(772,704),(843,1166),(-136,1227),(-124,767)],(224,248,231,180),4)
        self.line([(337,735),(350,1200)],(224,248,231,180),4)
        self.d.arc(self.bounds(257,839,457,1034),0,360,fill=(231,247,235,170),width=max(1,round(4*self.scale)))
        for i,(x,y,shirt) in enumerate([(109,988,TEAL),(592,1012,GOLD),(475,896,GOLD),(257,1070,TEAL)]):
            self.actor(x+15*math.sin(t*2+i),y,.76,t*1.7+i*.24,shirt,1 if i%2==0 else -1)
        self.actor(282+40*ease(t/length),1083,1.18,t*2.1,TEAL)
        path=ease((t-1.05)/1.47)
        bx=360+360*path
        by=1020-315*math.sin(path*math.pi*.74)
        for k in range(1,6):
            trail=ease(max(0,path-k*.045))
            xx=360+360*trail
            yy=1020-315*math.sin(trail*math.pi*.74)
            self.ell(xx-5,yy-5,xx+5,yy+5,(241,250,245,110-k*15))
        self.ell(bx-17,by-17,bx+17,by+17,WHITE)
        self.line([(bx-5,by-1),(bx+1,by-8),(bx+9,by+2)],(25,48,60),3)
    def goal(self,t,length):
        self.begin("goal")
        p=ease((t-.2)/1.18)
        self.glow(355,484,290,300,GOLD,100)
        self.poly([(0,767),(720,696),(720,1280),(0,1280)],(10,86,80))
        sx=(1-p)*6*math.sin(t*40)
        self.poly([(102+sx,349),(581+sx,349),(660+sx,971),(83+sx,971)],(15,43,62,207))
        self.line([(102+sx,349),(581+sx,349),(660+sx,971)],WHITE,13)
        self.line([(102+sx,349),(83+sx,971),(660+sx,971)],WHITE,10)
        for i in range(1,12):
            xx=102+i*42
            self.line([(xx+sx,351),(83+(xx-102)*1.2+sx,971)],(162,224,219,155),2)
        for yy in range(392,974,46):
            self.line([(100+sx,yy),(588+sx+(yy-349)*.13,yy)],(168,223,217,155),2)
        radius=22+103*p
        bx=351+28*p
        by=737-58*p
        self.glow(bx,by,radius*1.7,radius*1.7,GOLD,65)
        self.ell(bx-radius,by-radius,bx+radius,by+radius,WHITE)
        self.poly([(bx-.25*radius,by-.39*radius),(bx+.3*radius,by-.36*radius),
                   (bx+.48*radius,by+.06*radius),(bx+.04*radius,by+.42*radius),
                   (bx-.44*radius,by+.12*radius)],(14,38,54))
        rng=np.random.default_rng(21)
        age=max(0,t-.70)
        for i in range(114):
            a=rng.uniform(0,TWO_PI)
            speed=rng.uniform(110,680)
            x=360+math.cos(a)*speed*age
            y=660+math.sin(a)*speed*age+age*age*245
            if 0<x<720 and 0<y<1140:
                self.rect(x,y,x+5,y+12,(*[TEAL,GOLD,WHITE][i%3],210),1)
        if t>.70:self.txt("GOOOOL!",263,90,GOLD)
    def brand(self,t,length,brand,logo):
        self.begin("brand")
        self.glow(360,551,280,310,TEAL,112)
        self.glow(360,673,200,180,GOLD,53)
        for k in range(4):
            coords=[]
            for i in range(80):
                a=TWO_PI*i/79+t*.66+k*.3
                radius=156+k*20
                coords.append((360+radius*math.cos(a),544+radius*.69*math.sin(a)))
            self.line(coords,(*TEAL,90+k*22),2)
        if logo and Path(logo).is_file():
            im=Image.open(logo).convert("RGBA")
            im.thumbnail((round(280*self.sx),round(280*self.sy)))
            self.im.alpha_composite(im,(round((self.w-im.width)/2),round(405*self.sy)))
            self.d=ImageDraw.Draw(self.im)
        else:
            self.txt("UF",451,135,WHITE)
        self.txt("SUPER",786,83,WHITE)
        self.txt("SOCCER",883,96,GOLD)
        self.txt(brand,1074,29,TEAL)
    def frame(self,story,second,logo=None):
        shot,t=story.at(second)
        if shot.kind=="tunnel":self.tunnel(t,shot.duration)
        elif shot.kind=="pitch":self.pitch(t,shot.duration)
        elif shot.kind=="goal":self.goal(t,shot.duration)
        else:self.brand(t,shot.duration,story.brand,logo)
        self.dust(second)
        if shot.kind!="brand":
            self.rect(47,83,673,168,(5,18,39,210),20,(*TEAL,130))
            self.txt(shot.caption,101,34 if len(shot.caption)>17 else 40,GOLD)
        self.line([(57,1175),(661,1175)],(*TEAL,125),2)
        self.txt("UNIFORMER  /  ORIGINAL GAME WORLDS",1191,17,(192,224,231))
        alpha=max(1-ease(t/.22),ease((t-shot.duration+.22)/.22))
        if alpha>0:
            self.d.rectangle(self.bounds(0,0,720,1280),fill=(2,5,14,round(238*alpha)))
        return self.im.convert("RGB")

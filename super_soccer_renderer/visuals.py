"""Original vector-animated 2.5D football footage rendered by Pillow.

The engine is deliberately deterministic: the same storyboard and time always
produce the same frame. Coordinates are in a 720x1280 portrait stage.
"""
import math
from pathlib import Path
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 720, 1280
CYAN=(77,222,217)
GOLD=(255,195,103)
WHITE=(236,247,249)
DARK=(7,15,32)
TAU=math.tau


def clamp(x, lo=0, hi=1):
    return max(lo,min(hi,x))


def ease(x):
    x=clamp(x)
    return x*x*(3-2*x)


def interpolate(a,b,p):
    return a+(b-a)*p


@lru_cache(maxsize=40)
def text_font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if Path(path).is_file():
            return ImageFont.truetype(path,size)
    return ImageFont.load_default()


class Canvas:
    def __init__(self,width):
        if not 180 <= width <= 1080:
            raise ValueError("Width must be 180..1080")
        self.w=width
        self.h=round(width*H/W)
        self.s=width/W
        self.backgrounds={}
        for name,a,b in (
            ("tunnel",(6,10,28),(22,53,75)),
            ("pitch",(7,21,40),(19,73,87)),
            ("goal",(4,13,32),(10,51,71)),
            ("brand",(4,8,26),(18,39,67))):
            yy=np.linspace(0,1,self.h,dtype=np.float32)[:,None,None]
            xx=np.linspace(-1,1,self.w,dtype=np.float32)[None,:,None]
            vig=1-.26*(xx*xx)
            colors=(np.array(a,dtype=np.float32)*(1-yy)+np.array(b,dtype=np.float32)*yy)*vig
            self.backgrounds[name]=Image.fromarray(np.broadcast_to(colors,(self.h,self.w,3)).astype(np.uint8).copy()).convert("RGBA")

    def xy(self,x,y):
        return round(x*self.s),round(y*self.s)

    def bounds(self,x0,y0,x1,y1):
        return tuple(round(v*self.s) for v in (x0,y0,x1,y1))

    def begin(self,name):
        self.im=self.backgrounds[name].copy()
        self.d=ImageDraw.Draw(self.im)

    def poly(self,points,color):
        self.d.polygon([self.xy(x,y) for x,y in points],fill=color)

    def ellipse(self,x,y,r,fill,aspect=1):
        self.d.ellipse(self.bounds(x-r,y-r*aspect,x+r,y+r*aspect),fill=fill)

    def rect(self,box,fill,r=0,outline=None,width=1):
        box=self.bounds(*box)
        if r:
            self.d.rounded_rectangle(box,radius=round(r*self.s),fill=fill,outline=outline,width=max(1,round(width*self.s)))
        else:
            self.d.rectangle(box,fill=fill,outline=outline,width=max(1,round(width*self.s)))

    def line(self,pts,color,width=2):
        self.d.line([self.xy(x,y) for x,y in pts],fill=color,width=max(1,round(width*self.s)),joint="curve")

    def text(self,content,x,y,size,color=WHITE,anchor="mt",stroke=1):
        self.d.text(self.xy(x,y),content,font=text_font(max(9,round(size*self.s))),anchor=anchor,
                    fill=color,stroke_width=max(0,round(stroke*self.s)),stroke_fill=(5,13,24))

    def light(self,x,y,r,hexcolor,strength=.6):
        # A blurred additive-feeling light pool, physically behind characters.
        layer=Image.new("RGBA",self.im.size)
        d=ImageDraw.Draw(layer)
        d.ellipse(self.bounds(x-r,y-r,x+r,y+r),fill=(*hexcolor,round(110*strength)))
        layer=layer.filter(ImageFilter.GaussianBlur(max(1,round(r*.42*self.s))))
        self.im=Image.alpha_composite(self.im,layer)
        self.d=ImageDraw.Draw(self.im)

    def crowd(self,t,n=210):
        # Consistent, seeded spectators shimmering subtly instead of white noise.
        rng=np.random.default_rng(541)
        colors=[(63,151,171),(100,193,188),(244,190,103),(46,101,139)]
        for i in range(n):
            ang=rng.uniform(0,TAU)
            rx=rng.uniform(300,460)
            x=360+rx*math.cos(ang)
            y=518+rx*.44*math.sin(ang)
            if not 190<y<760 or not -10<x<730:continue
            twinkle=math.sin(t*2.6+i*1.43)
            r=1.1+1.5*(.5+.5*twinkle)
            self.ellipse(x,y,r,(*colors[i%4],255))

    def particles(self,t,n=65,y0=170,y1=1120,slant=0):
        rng=np.random.default_rng(805)
        for x0,y0p,z in rng.uniform(0,1,(n,3)):
            x=720*x0+slant*(1-z)+12*math.sin(t+z*9)
            y=y0+(y0p+t*(.065+z*.12))%1*(y1-y0)
            self.ellipse(x,y,.9+z*1.9,(*CYAN,round(75+160*z)))

    def player(self,x,y,scale,phase,jersey=CYAN,orientation=1,shadow=False):
        # All bones move as an articulated 2D skeleton; correctly connected neck.
        swing=math.sin(phase*TAU)
        x=float(x);y=float(y)
        col=(19,43,61) if shadow else jersey
        skin=(28,51,65) if shadow else (217,161,117)
        shorts=(19,34,56)
        shoes=(12,24,32) if shadow else (246,251,245)
        self.ellipse(x,y,43*scale,(2,10,18,125),.23)
        for side in (-1,1):
            hip=(x+side*11*scale,y-93*scale)
            knee=(hip[0]+side*swing*20*scale,y-(50-6*abs(swing))*scale)
            foot=(knee[0]+side*swing*22*scale+orientation*8*scale,y-6*scale)
            self.line((hip,knee,foot),shorts,13*scale)
            self.line((foot,(foot[0]+orientation*11*scale,foot[1])),shoes,10*scale)
        self.poly(((x-26*scale,y-171*scale),(x+25*scale,y-171*scale),
                   (x+26*scale,y-96*scale),(x-24*scale,y-96*scale)),col)
        self.poly(((x-25*scale,y-109*scale),(x+25*scale,y-109*scale),
                   (x+22*scale,y-88*scale),(x-22*scale,y-88*scale)),shorts)
        for side in (-1,1):
            shoulder=(x+side*25*scale,y-158*scale)
            elbow=(x+side*(43+6*swing)*scale,y-127*scale)
            hand=(x+side*(42+12*swing)*scale,y-98*scale)
            self.line((shoulder,elbow,hand),skin,11*scale)
            self.ellipse(*hand,5*scale,skin)
        self.rect((x-7*scale,y-190*scale,x+8*scale,y-165*scale),skin,4*scale)
        self.ellipse(x,y-209*scale,25*scale,skin,1.10)
        self.poly(((x-24*scale,y-221*scale),(x-16*scale,y-239*scale),
                   (x+10*scale,y-240*scale),(x+25*scale,y-219*scale),
                   (x+6*scale,y-228*scale),(x-15*scale,y-220*scale)),(10,20,32))
        if not shadow:
            self.ellipse(x+orientation*9*scale,y-209*scale,1.8*scale,(13,29,37))
            self.line(((x+orientation*4*scale,y-197*scale),(x+orientation*12*scale,y-196*scale)),(108,67,62),1)

    def ball(self,x,y,r,rotation=0):
        self.ellipse(x,y+8*r/14,r*.94,(3,11,19,95),.34)
        self.ellipse(x,y,r,WHITE)
        a=rotation
        pts=[(x+r*.4*math.cos(a+j*TAU/5),y+r*.4*math.sin(a+j*TAU/5)) for j in range(5)]
        self.poly(pts,(25,46,57))
        for j in range(5):
            self.line((pts[j],(x+r*.83*math.cos(a+j*TAU/5),y+r*.83*math.sin(a+j*TAU/5))),(25,46,57),1)

    def editorial(self,shot,index,t):
        # Small consistent label system, not a slideshow title replacing footage.
        self.rect((43,61,677,130),(5,16,35,225),r=16,outline=(53,138,157),width=2)
        size=29 if len(shot.caption)>=19 else 34
        self.text(shot.caption,360,77,size,GOLD)
        self.rect((41,151,98,191),(7,24,40,224),r=9,outline=CYAN)
        self.text(f"{index+1:02d}",69,156,21,CYAN)
        self.line(((48,1206),(672,1206)),(65,148,160),2)
        self.text("UNIFORMER STUDIO  •  ORIGINAL GAME WORLDS",360,1220,18,(176,220,230))
        # Fade at shot boundaries, gentle enough not to hide the cut.
        darkness=max(0,int(210*(1-ease(t/.18)))) + max(0,int(225*ease((t-shot.seconds+.15)/.15)))
        if darkness:
            self.rect((0,0,720,1280),(4,7,18,min(245,darkness)))

    def tunnel(self,shot,t):
        self.begin("tunnel")
        progress=ease(t/shot.seconds)
        vp=430+round(28*progress)
        self.light(360,vp,245,CYAN,1)
        self.poly(((0,0),(720,0),(480,vp),(240,vp)),(14,28,48))
        self.poly(((0,0),(240,vp),(178,1030),(0,1230)),(25,49,69))
        self.poly(((720,0),(480,vp),(550,1030),(720,1230)),(14,31,52))
        self.poly(((240,vp),(480,vp),(505,949),(207,949)),(42,142,149))
        self.poly(((0,1280),(207,949),(505,949),(720,1280)),(12,28,47))
        for k in range(1,8):
            a=k/8
            y=949+(1280-949)*a*a
            xmin=207*(1-a)
            xmax=505+(720-505)*a
            self.line(((xmin,y),(xmax,y)),(54,145,144),2)
        for i in range(5):
            y=95+i*170
            self.line(((34,y),(180,y+92)),(86,215,220),7)
            self.line(((686,y),(540,y+92)),(86,215,220),7)
        self.line(((206,947),(20,1270)),(79,215,209),5)
        self.line(((505,947),(692,1270)),(79,215,209),5)
        self.particles(t,49,370,1160)
        # Silhouetted athlete moving toward the end of the tunnel.
        x=361+22*math.sin(t*.75)
        y=1067-135*progress
        self.player(x,y,1.12-.2*progress,t*2.3,(29,68,80),orientation=-1,shadow=True)
        self.editorial(shot,0,t)

    def pitch(self,shot,t):
        self.begin("pitch")
        # Layered stadium architecture and individual crowd particles.
        self.ellipse(360,526,530,(13,41,63),.68)
        self.ellipse(360,520,466,(33,74,82),.66)
        self.ellipse(360,520,408,(8,26,47),.67)
        self.crowd(t)
        for x in (130,570):
            self.light(x,260,150,(181,240,235),.65)
            self.line(((x,158),(x,275)),(215,250,241),13)
            self.ellipse(x,255,15,WHITE)
        self.poly(((-100,790),(800,705),(820,1230),(-130,1245)),(10,89,84))
        for j in range(8):
            self.poly(((-130,800+j*69),(810,710+j*69),(820,743+j*69),(-140,836+j*69)),(13,110,99))
        self.line(((-105,827),(782,744),(812,1189),(-107,1210),(-105,827)),(219,244,235),4)
        self.line(((351,783),(352,1200)),(218,247,237),4)
        self.d.arc(self.bounds(270,865,452,1070),0,360,fill=(215,246,240),width=max(1,round(self.s*4)))
        # Parallax players with independent gait and opposite team jerseys.
        for i,(x,y,shirt,phase) in enumerate(((126,1055,CYAN,0.1),(582,1010,GOLD,.32),
              (460,926,GOLD,.48),(228,932,CYAN,.8))):
            self.player(x+22*math.sin(t*.8+i),y,0.70,t*1.3+phase,shirt,orientation=1 if i%2 else -1)
        mainx=275+55*ease(t/shot.seconds)
        self.player(mainx,1135,1.19,t*2.05,CYAN)
        fly=ease((t-.85)/(shot.seconds-1.05))
        bx=350+310*fly
        by=1043-272*math.sin(fly*2.36)
        for i in range(5,0,-1):
            past=clamp(fly-i*.035)
            x=350+310*past
            y=1043-272*math.sin(past*2.36)
            self.ellipse(x,y,6,(117,226,224,95))
        self.ball(bx,by,17+8*fly,t*6)
        self.editorial(shot,1,t)

    def goal(self,shot,t):
        self.begin("goal")
        p=ease((t-.30)/(shot.seconds*.57))
        shake=10*math.sin(t*33)*(1-p)
        self.light(362,466,260,GOLD,.8)
        self.poly(((-40,824),(750,736),(740,1280),(-20,1280)),(7,86,74))
        # Mesh over an independently zooming keeper dive.
        x0=95+shake; x1=594+shake
        self.poly(((x0,341),(x1,341),(663+shake,1029),(68+shake,1029)),(13,45,63))
        for k in range(13):
            x=x0+k*41.6
            self.line(((x,344),(68+(x-x0)*1.20+shake,1027)),(115,184,191),2)
        for y in range(401,1020,49):
            self.line(((x0-2,y),(x1+(y-341)*.105,y)),(115,184,191),2)
        self.line(((x0,1028),(x0,341),(x1,341),(663+shake,1028)),WHITE,12)
        self.line(((x0,1028),(663+shake,1028)),WHITE,9)
        # Keeper moves toward the ball, but does not freeze on the line.
        ky=1095-90*p
        kx=230+168*p
        self.player(kx,ky,.94,t*1.9,(236,102,84),orientation=-1)
        bx=350+80*p
        by=845-205*p
        radius=19+92*p
        self.ball(bx,by,radius,t*2.7)
        rng=np.random.default_rng(193)
        if t>.75:
            age=t-.75
            for j in range(104):
                a=rng.uniform(0,TAU)
                v=rng.uniform(130,580)
                x=360+math.cos(a)*v*age
                y=670+math.sin(a)*v*age+age*age*180
                if -8<x<728 and 0<y<1200:
                    self.rect((x,y,x+5,y+11),CYAN if j%2 else GOLD,r=1)
            self.text("¡GOOOL!",360,245,105,GOLD,stroke=4)
        self.editorial(shot,2,t)

    def brand(self,shot,t,brand,logo=None):
        self.begin("brand")
        self.light(360,533,300,CYAN,1)
        self.light(350,844,170,GOLD,.33)
        for ring in range(4):
            pts=[]
            for j in range(70):
                a=j*TAU/69+t*.32+ring*.24
                r=205+ring*26
                pts.append((360+r*math.cos(a),541+r*.64*math.sin(a)))
            self.line(pts,(49+ring*13,143+ring*18,166+ring*15),2)
        self.particles(t,74,250,1100)
        if logo and Path(logo).is_file():
            image=Image.open(logo).convert("RGBA")
            image.thumbnail((round(320*self.s),round(270*self.s)),Image.Resampling.LANCZOS)
            self.im.alpha_composite(image,((self.w-image.width)//2,round(410*self.s)))
            self.d=ImageDraw.Draw(self.im)
        else:
            self.text("UF",360,423,177,WHITE,stroke=4)
        self.text("SUPER",360,796,94,WHITE,stroke=3)
        self.text("SOCCER",360,899,99,GOLD,stroke=3)
        self.text(brand,360,1070,31,CYAN)
        self.editorial(shot,3,t)

    def frame(self,story,time,logo=None):
        index,shot,local=story.locate(time)
        if shot.kind=="tunnel":self.tunnel(shot,local)
        elif shot.kind=="pitch":self.pitch(shot,local)
        elif shot.kind=="goal":self.goal(shot,local)
        else:self.brand(shot,local,story.brand,logo)
        return self.im.convert("RGB")

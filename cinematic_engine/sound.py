"""Original soundtrack synthesized in NumPy; no third-party recordings."""
import math
import wave
from pathlib import Path
import numpy as np

def compose(path,seconds,sr=32000):
    n=round(seconds*sr)
    t=np.arange(n,dtype=np.float32)/sr
    mix=np.zeros(n,dtype=np.float32)
    chords=[(110.,164.8,220.),(98.,146.8,196.),(130.8,164.8,261.6),(110.,146.8,220.)]
    for i,start in enumerate(np.arange(0,seconds,2.5)):
        mask=(t>=start)&(t<start+2.55)
        x=t[mask]-start
        env=np.sin(np.pi*np.minimum(x/2.55,1))**.7
        mix[mask]+=.19*env*sum(np.sin(math.tau*f*x) for f in chords[i%4])/3
    for beat in np.arange(.1,seconds,.5):
        mask=(t>=beat)&(t<beat+.18)
        x=t[mask]-beat
        mix[mask]+=.25*np.sin(math.tau*(60*x+120*x*x))*np.exp(-25*x)
    for impact in (2.1,5.2,7.6):
        mask=(t>=impact)&(t<impact+.48)
        x=t[mask]-impact
        mix[mask]+=.16*np.sin(math.tau*(550*x+800*x*x))*np.exp(-8*x)
    rng=np.random.default_rng(67)
    mask=(t>=5.3)&(t<8.5)
    mix[mask]+=.08*rng.normal(size=mask.sum())*np.sin(np.pi*(t[mask]-5.3)/3.2)
    pcm=(np.tanh(mix*1.4)*.70*32767).astype("<i2")
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(pcm.tobytes())

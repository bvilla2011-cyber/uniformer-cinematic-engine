"""Deterministic original synthesis: music pad, heartbeat and football SFX."""
from pathlib import Path
import math
import wave
import numpy as np

TAU = math.tau


def compose(path, story, sample_rate=22050):
    n = int(story.duration*sample_rate)
    t = np.arange(n, dtype=np.float32) / sample_rate
    a = np.zeros(n, dtype=np.float32)
    chords = ((110,164.81,220),(98,146.83,196),(130.81,164.81,261.63),(110,146.83,220))
    for j, start in enumerate(np.arange(0,story.duration,2.5)):
        end=min(start+2.5,story.duration)
        first, last=round(start*sample_rate), round(end*sample_rate)
        q=t[first:last]-start
        env=np.minimum(1,np.maximum(0,q)/.25)*np.minimum(1,np.maximum(0,end-start-q)/.45)
        pad=sum(np.sin(TAU*f*q + .18*np.sin(TAU*.6*q)) for f in chords[j%4])/3
        a[first:last]+=.12*env*pad
    for beat in np.arange(.15, story.duration, .52):
        i=int(beat*sample_rate)
        length=min(n-i,int(.20*sample_rate))
        if length<=0: continue
        q=np.arange(length,dtype=np.float32)/sample_rate
        a[i:i+length]+=.21*np.sin(TAU*(65*q + 80*q*q))*np.exp(-24*q)
    # Air movement, a kick, a struck goalpost, and stadium-like original crowd noise.
    rng=np.random.default_rng(825)
    noise=rng.standard_normal(n).astype(np.float32)
    event_times=[]
    clock=0
    for shot in story.shots:
        if shot.kind in {"pitch","goal"}:
            event_times.append((clock+.45, "kick" if shot.kind=="pitch" else "impact"))
        clock+=shot.seconds
    for start, event in event_times:
        i=round(start*sample_rate)
        count=min(n-i,round(.55*sample_rate))
        if count<=0:continue
        q=np.arange(count,dtype=np.float32)/sample_rate
        kick=.4*np.sin(TAU*(105*q - 75*q*q))*np.exp(-16*q)
        sizzle=.09*noise[i:i+count]*np.exp(-17*q)
        if event=="impact":
            kick+=.20*np.sin(TAU*280*q)*np.exp(-8*q)
        a[i:i+count]+=kick+sizzle
    # Dynamic master limiting without clipping.
    a=np.tanh(a*1.55)*.75
    pcm=(a*32767).astype("<i2")
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return path

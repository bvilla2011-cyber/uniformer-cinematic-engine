"""Validated storyboards; model-produced input is never executable code."""
import json
import math
from pathlib import Path
from dataclasses import dataclass

DEFAULT={"title":"El estadio despierta","brand":"UNIFORMER STUDIO","shots":[
 {"kind":"tunnel","duration":2.1,"caption":"TODO EMPIEZA AQUÍ"},
 {"kind":"pitch","duration":3.0,"caption":"CAMBIA EL PARTIDO"},
 {"kind":"goal","duration":2.5,"caption":"ES TU MOMENTO"},
 {"kind":"brand","duration":2.4,"caption":"SUPER SOCCER"}]}
KINDS={"tunnel","pitch","goal","brand"}

@dataclass(frozen=True)
class Shot:
    kind:str
    duration:float
    caption:str

@dataclass(frozen=True)
class Story:
    title:str
    brand:str
    shots:tuple
    @property
    def duration(self): return sum(s.duration for s in self.shots)
    def at(self,t):
        start=0
        for s in self.shots:
            if t<start+s.duration: return s,max(0,t-start)
            start+=s.duration
        return self.shots[-1],self.shots[-1].duration

def _label(s,maxlen):
    if not isinstance(s,str) or not 1<=len(s.strip())<=maxlen or any(ord(c)<32 for c in s):
        raise ValueError("Bad caption or label")
    return s.strip()

def validate(data):
    if not isinstance(data,dict) or not isinstance(data.get("shots"),list) or not 1<=len(data["shots"])<=12:
        raise ValueError("Requires 1-12 shots")
    shots=[]
    for x in data["shots"]:
        if not isinstance(x,dict) or x.get("kind") not in KINDS: raise ValueError("Invalid shot kind")
        d=x.get("duration")
        if isinstance(d,bool) or not isinstance(d,(int,float)) or not math.isfinite(d) or not .3<=d<=12:
            raise ValueError("Bad duration")
        shots.append(Shot(x["kind"],float(d),_label(x.get("caption"),48)))
    output=Story(_label(data.get("title","Sin título"),100),_label(data.get("brand","UNIFORMER STUDIO"),42),tuple(shots))
    if output.duration>60: raise ValueError("Too long")
    return output

def load(path=None):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")) if path else DEFAULT)

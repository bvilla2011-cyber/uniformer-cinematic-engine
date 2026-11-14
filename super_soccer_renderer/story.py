"""Validated, version-controlled cinematic scene schema.

Model output is always data, never executable code.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path

KINDS = {"tunnel", "pitch", "goal", "brand"}

@dataclass(frozen=True)
class Shot:
    kind: str
    seconds: float
    caption: str

@dataclass(frozen=True)
class Story:
    title: str
    brand: str
    shots: tuple[Shot, ...]

    @property
    def duration(self):
        return sum(s.seconds for s in self.shots)

    def locate(self, time):
        elapsed = 0.0
        for index, shot in enumerate(self.shots):
            if time < elapsed + shot.seconds:
                return index, shot, max(0.0, time - elapsed)
            elapsed += shot.seconds
        return len(self.shots)-1, self.shots[-1], self.shots[-1].seconds


def _label(value, maxlen):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maxlen:
        raise ValueError(f"Text must contain 1-{maxlen} characters")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("Control characters are not supported")
    return value.strip()


def validate(raw):
    if not isinstance(raw, dict):
        raise ValueError("Storyboard must be a JSON object")
    title = _label(raw.get("title", "Untitled"), 80)
    brand = _label(raw.get("brand", "UNIFORMER STUDIO"), 40)
    shots = raw.get("shots")
    if not isinstance(shots, list) or not 1 <= len(shots) <= 12:
        raise ValueError("Required: 1 to 12 shots")
    parsed = []
    for shot in shots:
        if not isinstance(shot, dict) or shot.get("kind") not in KINDS:
            raise ValueError("Unknown scene kind")
        seconds = shot.get("seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 0.3 <= seconds <= 12:
            raise ValueError("seconds must be between 0.3 and 12")
        caption = _label(shot.get("caption", ""), 45)
        parsed.append(Shot(shot["kind"], float(seconds), caption))
    story = Story(title, brand, tuple(parsed))
    if story.duration > 60:
        raise ValueError("Total duration cannot exceed 60 seconds")
    return story


def load(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))

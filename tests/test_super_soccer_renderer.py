from pathlib import Path
import math
import wave
import pytest
from super_soccer_renderer.story import validate, load
from super_soccer_renderer.audio import compose
from super_soccer_renderer.visuals import Canvas
from super_soccer_renderer.render import PROFILES

SCENE = "scenes/super_soccer.json"


def test_story_validated():
    story=load(SCENE)
    assert math.isclose(story.duration,11.8)
    assert len(story.shots)==4
    assert story.locate(0)[1].kind=="tunnel"
    assert story.locate(11.7)[1].kind=="brand"


@pytest.mark.parametrize("case",[
    {"shots":[{"kind":"unapproved","seconds":3,"caption":"Hello"}]},
    {"shots":[{"kind":"goal","seconds":float("nan"),"caption":"Hello"}]},
    {"shots":[{"kind":"goal","seconds":-1,"caption":"Hello"}]},
    {"shots":[{"kind":"goal","seconds":3,"caption":""}]},
    {"shots":[]},
])
def test_story_rejects_bad_data(case):
    with pytest.raises(ValueError):
        validate(case)


def test_all_shots_generate_image():
    scene=load(SCENE)
    screen=Canvas(216)
    elapsed=0
    images=[]
    for shot in scene.shots:
        im=screen.frame(scene,elapsed+shot.seconds*.5)
        assert im.mode=="RGB"
        assert im.size==(216,384)
        images.append(im.getpixel((108,190)))
        elapsed+=shot.seconds
    assert len(set(images))>=3


def test_score(tmp_path):
    result=compose(tmp_path/"score.wav",load(SCENE))
    with wave.open(str(result),"rb") as f:
        assert f.getnchannels()==1
        assert f.getnframes()>200000

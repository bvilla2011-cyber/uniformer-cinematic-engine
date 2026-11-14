import pytest
from cinematic_engine.story import load,validate
from cinematic_engine.visuals import Stage
from cinematic_engine.sound import compose

def test_timeline():
    s=load()
    assert s.duration==pytest.approx(10)
    assert s.at(0)[0].kind=="tunnel"
    assert s.at(9.5)[0].kind=="brand"

@pytest.mark.parametrize("shot",[
 {"kind":"bad","duration":1,"caption":"X"},
 {"kind":"goal","duration":float("nan"),"caption":"X"},
 {"kind":"goal","duration":-1,"caption":"X"},
 {"kind":"goal","duration":1,"caption":""}])
def test_invalid_stories(shot):
    with pytest.raises(ValueError):
        validate({"shots":[shot]})

def test_every_scene_is_drawn():
    s=load();stage=Stage(216,384);t=0
    for shot in s.shots:
        im=stage.frame(s,t+shot.duration/2)
        assert im.size==(216,384)
        assert im.mode=="RGB"
        t+=shot.duration

def test_sound(tmp_path):
    path=tmp_path/"audio.wav"
    compose(path,1.2)
    assert path.stat().st_size>10000

def test_ai_director_is_offline_by_default(tmp_path):
    from cinematic_engine.director import run
    manifest=tmp_path/"plan.json"
    plan=run(manifest=str(manifest))
    assert manifest.is_file()
    assert len(plan["shots"])==4
    assert all("World bible" in s["prompt"] for s in plan["shots"])
    assert plan["status"]=="planned_only_no_generation"

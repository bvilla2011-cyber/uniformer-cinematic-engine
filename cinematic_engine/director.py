"""Structured multi-shot director for optional AI-assisted video production.

Creates consistent, auditable prompts. Nothing is sent to a provider unless
--generate is explicitly selected. No untrusted LLM-generated Python runs.
"""
import argparse
import json
from pathlib import Path
from .story import load

STYLE=(
 "Original cinematic 2.5D low-poly animation for a fictional soccer management game. "
 "Hand-crafted angular shapes, precise character animation, rich volumetric stadium lighting, "
 "cyan and amber accents over midnight-navy shadows, graceful motion, meticulous sound. "
 "No existing IP, logos, copyrighted characters, text overlays, or borrowed music. "
 "Consistent world, wardrobe and lighting throughout the sequence. "
)
WORLD=(
 "World bible: one monumental football stadium at night, teal running lights, "
 "warm gold flare accents, mist in the air, a confident original athlete "
 "with short dark hair in an unbranded teal kit and navy shorts. "
 "All shots must depict the exact same original athlete and venue. "
)
DIRECTIONS={
    "tunnel":("The athlete runs out of a concrete players' tunnel toward the enormous illuminated pitch.",
              "Low tracking dolly from behind, footsteps, dramatic depth from tunnel pillars."),
    "pitch":("The same athlete receives a pass, controls the ball, and launches a long curling shot; opponents react.",
             "Low touchline tracking camera with physically motivated pan; player and ball animate independently."),
    "goal":("The football strikes the upper net; the mesh deforms, confetti bursts, stadium crowd reacts.",
            "Close-up fast ball follow into the goal, short impact shake, slow motion only after impact."),
    "brand":("The pitch lights sweep across an original abstract geometric soccer emblem; dramatic closing tableau.",
             "Camera cranes upward, motion gradually decelerates, clean negative space for later approved brand overlay.")
}

def plan(story):
    result=[]
    for i,shot in enumerate(story.shots,1):
        action,camera=DIRECTIONS[shot.kind]
        prompt=f"{STYLE} {WORLD} Shot {i}: {action} Camera direction: {camera} "
        prompt+=f"Scene duration: approximately {shot.duration:.1f}s. No cut within this shot."
        result.append({"index":i,"kind":shot.kind,"duration":shot.duration,
                       "caption":shot.caption,"camera":camera,"prompt":prompt,
                       "filename":f"shot_{i:02d}.mp4"})
    return {"title":story.title,"brand":story.brand,"continuity_bible":WORLD,
            "shots":result,"status":"planned_only_no_generation"}

def run(story_path=None,manifest="dist/shot-plan.json",generate=False,video_dir="dist/ai_shots",master_output="dist/ai_master.mp4"):
    story=load(story_path)
    sequence=plan(story)
    path=Path(manifest)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(sequence,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("Created prompt storyboard:",path)
    if not generate:
        return sequence
    from .video_api import generate as video_generate
    from .master import combine
    directory=Path(video_dir)
    directory.mkdir(parents=True,exist_ok=True)
    outputs=[]
    for shot in sequence["shots"]:
        target=directory/shot["filename"]
        video_generate(shot["prompt"],str(target),duration=max(1,min(12,round(shot["duration"]))))
        outputs.append(target)
    combine(outputs,master_output)
    sequence["status"]="generated_and_composed"
    path.write_text(json.dumps(sequence,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return sequence

def main():
    p=argparse.ArgumentParser(description="Plan original consistent AI video shots or generate through your configured provider")
    p.add_argument("--story")
    p.add_argument("--output",default="dist/shot-plan.json")
    p.add_argument("--generate",action="store_true",help="Opt in to provider calls, may spend usage quota")
    p.add_argument("--video-dir",default="dist/ai_shots")
    p.add_argument("--master",default="dist/ai_master.mp4")
    a=p.parse_args()
    run(a.story,a.output,a.generate,a.video_dir,a.master)
if __name__=="__main__":
    main()

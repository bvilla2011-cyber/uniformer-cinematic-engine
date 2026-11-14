"""Procedural 3D low-poly SUPER SOCCER launch teaser.

Run with:
  blender -b --python blender_super_soccer.py -- --preview --output /tmp/teaser.mp4
  blender -b --python blender_super_soccer.py -- --output output/super_soccer_3d.mp4

An existing narration can be preserved with --voiceover narration.wav.
"""
import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import wave

import numpy as np

import bpy
from mathutils import Vector

FPS = 24
DURATION = 18
TAU = math.tau


def args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/super_soccer_3d.mp4")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--stills", action="store_true", help="Render representative review frames only")
    p.add_argument("--voiceover")
    p.add_argument("--music", help="Optional licensed/original score file")
    p.add_argument("--subtitles", help="Optional timed SRT sidecar")
    p.add_argument("--logo")
    return p.parse_args(raw)


def mat(name, color, rough=.7, metallic=0, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return m


def assign(obj, material):
    obj.data.materials.append(material)
    return obj


def bevel(obj, amount=.08, segments=1):
    mod = obj.modifiers.new("Low-poly edge highlights", "BEVEL")
    mod.width = amount
    mod.segments = segments
    obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def cube(name, loc, scale, material, edge=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(o, material)
    if edge:
        bevel(o, edge)
    return o


def ico(name, loc, scale, material, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    assign(o, material)
    return o


def cylinder_between(name, a, b, radius, material, vertices=7):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=d.length, location=(a+b)/2)
    o = bpy.context.object
    o.name = name
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    assign(o, material)
    bevel(o, .025)
    return o


def area_light(name, loc, target, power, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def animate(obj, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert(data_path="location", frame=frame)
    if rot is not None:
        obj.rotation_euler = rot
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert(data_path="scale", frame=frame)


def add_cycles(obj):
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            fc.modifiers.new("CYCLES")


def actor(name, loc, shirt, shorts, skin, hair, shoes, run=True):
    root = bpy.data.objects.new(name + " | actor root", None)
    bpy.context.collection.objects.link(root)
    root.location = loc
    root.empty_display_size = .35
    torso = cube(name+" | faceted shirt", (0,0,0), (1.00,.58,1.18), shirt, .10)
    torso.parent = root
    torso.location = (0,0,2.28)
    bib = cube(name+" | angular chest panel", (0,0,0), (.49,.605,.72), shirt, .035)
    bib.parent = root
    bib.location = (0,-.012,2.35)
    shorts_obj = cube(name+" | shorts", (0,0,0), (.89,.56,.48), shorts, .07)
    shorts_obj.parent = root
    shorts_obj.location = (0,0,1.53)
    head = ico(name+" | low-poly head", (0,0,0), (.36,.34,.43), skin, 2)
    head.parent = root
    head.location = (0,-.015,3.24)
    hair_obj = ico(name+" | hair", (0,0,0), (.37,.35,.22), hair, 1)
    hair_obj.parent = root
    hair_obj.location = (0,.015,3.52)
    # Small nose and brow plane give the profile direction without a detailed face.
    nose = ico(name+" | nose", (0,0,0), (.085,.105,.09), skin, 1)
    nose.parent = root
    nose.location = (0,-.34,3.23)
    for side in (-1, 1):
        # Pivot at each hip. Cylinders are modeled down the local -Z axis.
        hip = bpy.data.objects.new(name+f" | hip {side}", None)
        bpy.context.collection.objects.link(hip)
        hip.parent = root
        hip.location = (side*.24,0,1.42)
        upper = cylinder_between(name+" | thigh", (0,0,0), (0,0,-.68), .16, shorts)
        upper.parent = hip
        upper.location = (0,0,-.34)
        knee = bpy.data.objects.new(name+f" | knee {side}", None)
        bpy.context.collection.objects.link(knee)
        knee.parent = hip
        knee.location = (0,0,-.66)
        lower = cylinder_between(name+" | shin", (0,0,0), (0,0,-.72), .105, skin)
        lower.parent = knee
        lower.location = (0,0,-.36)
        foot = cube(name+" | boot", (0,0,0), (.22,.42,.14), shoes, .035)
        foot.parent = knee
        foot.location = (0,-.16,-.72)
        if run:
            for f, angle in ((1,-.40),(7,.42),(13,-.40)):
                animate(hip, f, rot=(angle*side,0,0))
            add_cycles(hip)
            for f, angle in ((1,.18),(7,.62),(13,.18)):
                animate(knee, f, rot=(angle if side == 1 else angle*.25,0,0))
            add_cycles(knee)
        shoulder = bpy.data.objects.new(name+f" | shoulder {side}", None)
        bpy.context.collection.objects.link(shoulder)
        shoulder.parent = root
        shoulder.location = (side*.53,0,2.72)
        arm = cylinder_between(name+" | sleeve", (0,0,0), (side*.13,0,-.48), .19, shirt)
        arm.parent = shoulder
        arm.location = (side*.065,0,-.24)
        elbow = bpy.data.objects.new(name+f" | elbow {side}", None)
        bpy.context.collection.objects.link(elbow)
        elbow.parent = shoulder
        elbow.location = (side*.13,0,-.47)
        fore = cylinder_between(name+" | forearm", (0,0,0), (side*.04,-.02,-.47), .115, skin)
        fore.parent = elbow
        fore.location = (side*.02,-.01,-.235)
        hand = ico(name+" | hand", (0,0,0), (.13,.14,.13), skin, 1)
        hand.parent = elbow
        hand.location = (side*.04,-.02,-.49)
        if run:
            for f, angle in ((1,-.50),(7,.50),(13,-.50)):
                animate(shoulder, f, rot=(angle*side,0,0))
            add_cycles(shoulder)
    return root


def text_obj(body, name, material, size, parent, loc, extrude=.003):
    data = bpy.data.curves.new(name, "FONT")
    data.body = body
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    data.size = size
    data.extrude = extrude
    data.bevel_depth = .002
    bold_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if Path(bold_font).is_file():
        data.font = bpy.data.fonts.load(bold_font, check_existing=True)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    assign(obj, material)
    obj.parent = parent
    obj.location = loc
    return obj


def ring(name, parent, loc, radius, material):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = .012
    data.bevel_resolution = 2
    spline = data.splines.new("POLY")
    spline.points.add(95)
    for i, p in enumerate(spline.points):
        a = TAU*i/96
        p.co = (radius*math.cos(a), radius*math.sin(a), 0, 1)
    spline.use_cyclic_u = True
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    assign(obj, material)
    obj.parent = parent
    obj.location = loc
    return obj


def image_panel(path, parent, loc, height):
    image = bpy.data.images.load(str(path), check_existing=True)
    aspect = image.size[0] / max(1, image.size[1])
    w = height * aspect
    mesh = bpy.data.meshes.new("Brand logo plane mesh")
    mesh.from_pydata([(-w/2,-height/2,0),(w/2,-height/2,0),(w/2,height/2,0),(-w/2,height/2,0)],[],[(0,1,2,3)])
    uv = mesh.uv_layers.new(name="Logo UV")
    for loop, coord in zip(mesh.loops, ((0,0),(1,0),(1,1),(0,1))):
        uv.data[loop.index].uv = coord
    material = bpy.data.materials.new("Official RGBA brand logo")
    material.use_nodes = True
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    elif hasattr(material, "blend_method"):
        material.blend_method = "BLEND"
    nodes = material.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    material.node_tree.links.new(texture.outputs["Color"],shader.inputs["Base Color"])
    material.node_tree.links.new(texture.outputs["Alpha"],shader.inputs["Alpha"])
    mesh.materials.append(material)
    obj = bpy.data.objects.new("Official logo overlay",mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = loc
    return obj


def synth_score(path, duration=DURATION, sample_rate=48000):
    """Make an original, deterministic cinematic bed with pulse, plucks and impacts."""
    n = int(duration*sample_rate)
    t = np.arange(n,dtype=np.float32)/sample_rate
    mix = np.zeros(n,dtype=np.float32)
    progressions = ((55.0,82.41,110.0,164.81),(43.65,65.41,87.31,130.81),
                    (65.41,98.0,130.81,196.0),(49.0,73.42,98.0,146.83))
    for i,start in enumerate((0,4.2,8.4,12.6)):
        end=min(duration,start+5.4)
        lo,hi=int(start*sample_rate),int(end*sample_rate)
        q=t[lo:hi]-start
        env=np.minimum(1,q/.85)*np.minimum(1,(end-start-q)/.9)
        chord=np.zeros_like(q)
        for j,f in enumerate(progressions[i]):
            chord += np.sin(2*np.pi*f*q+.08*np.sin(2*np.pi*.22*q)+j*.03)/(1+j*.55)
        mix[lo:hi] += .11*env*chord
    # Restrained four-on-the-floor pulse; long decay makes it cinematic rather than dance music.
    for beat in np.arange(.25,duration,.5):
        lo=int(beat*sample_rate)
        size=min(int(.34*sample_rate),n-lo)
        q=np.arange(size,dtype=np.float32)/sample_rate
        mix[lo:lo+size] += .19*np.sin(2*np.pi*(77*q-94*q*q))*np.exp(-q*13)
        if int(beat*2)%4 in (1,3):
            mix[lo:lo+size] += .022*np.sin(2*np.pi*880*q)*np.exp(-q*28)
    # A six-note upper arpeggio adds movement across the stadium reveal.
    scale=(0,3,7,10,7,3)
    root=110.0
    for i,beat in enumerate(np.arange(.5,duration,.25)):
        lo=int(beat*sample_rate)
        size=min(int(.20*sample_rate),n-lo)
        q=np.arange(size,dtype=np.float32)/sample_rate
        f=root*2**(scale[i%len(scale)]/12)
        tone=np.sin(2*np.pi*f*q)+.25*np.sin(2*np.pi*f*2*q)
        mix[lo:lo+size] += .028*tone*np.exp(-q*14)
    # Transition impacts and bright metallic tails.
    for event in (4.0,8.0,11.0,13.8):
        lo=int(event*sample_rate)
        size=min(int(.75*sample_rate),n-lo)
        q=np.arange(size,dtype=np.float32)/sample_rate
        boom=.30*np.sin(2*np.pi*(52*q-18*q*q))*np.exp(-q*7)
        ring=.07*np.sin(2*np.pi*410*q)*np.exp(-q*4)
        mix[lo:lo+size] += boom+ring
    # Final cinematic swell, kept below speech level.
    lo=int(12.2*sample_rate)
    q=t[lo:]
    rise=np.clip((q-12.2)/4.2,0,1)
    mix[lo:] += .045*rise*np.sin(2*np.pi*196*q+.2*np.sin(2*np.pi*.4*q))
    mix=np.tanh(mix*1.65)*.72
    pcm=np.int16(np.clip(mix,-.98,.98)*32767)
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())
    return Path(path)


def build_scene(logo=None):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    mats = {
        "navy": mat("Arcade ink #101335", (.018,.024,.13), .32, .25),
        "wall": mat("Arcade navy #151b4d", (.027,.045,.19), .55),
        "purple": mat("Arcade purple #7650dd", (.20,.12,.58), .4, .12),
        "blue": mat("Arcade blue #2864ee", (.045,.20,.78), .38, .12),
        "cyan": mat("Arcade cyan #56e7e0", (.045,.68,.64), .32, .15),
        "mint": mat("Cyan light strip emission", (.13,.88,.82), .3, emission=4),
        "gold": mat("Arcade yellow #ffe35b", (1.0,.84,.26), .35, .55),
        "grass1": mat("Pitch deep green", (.025,.22,.14), .8),
        "grass2": mat("Pitch lit green", (.035,.31,.18), .8),
        "line": mat("Pitch chalk", (.73,.90,.78), .55),
        "steel": mat("Goal frame", (.77,.9,.88), .24, .65),
        "skin1": mat("Player skin warm", (.54,.29,.18), .8),
        "skin2": mat("Player skin bronze", (.72,.43,.28), .8),
        "hair": mat("Hair charcoal", (.018,.025,.03), .8),
        "shorts": mat("Midnight shorts", (.018,.052,.08), .55),
        "goldshirt": mat("Arcade yellow away shirt", (.98,.68,.10), .42),
        "redshirt": mat("Arcade coral keeper shirt", (.94,.28,.20), .5),
        "boots": mat("Porcelain boots", (.82,.88,.84), .45),
        "seat1": mat("Stand arcade navy", (.03,.045,.21), .7),
        "seat2": mat("Stand arcade purple", (.16,.10,.42), .7),
        "crowd1": mat("Crowd cyan", (.08,.58,.58), .65),
        "crowd2": mat("Crowd yellow", (.90,.67,.14), .65),
        "ballwhite": mat("Ball ivory", (.85,.91,.87), .25),
        "ballblack": mat("Ball graphite", (.025,.045,.055), .3),
        "whiteglow": mat("Arcade paper white", (.98,.97,.87), .25, emission=1.3),
        "coral": mat("Arcade coral #ff876f", (.95,.30,.22), .35, emission=.25),
    }
    world = bpy.data.worlds.new("Night match atmosphere") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.012,.024,.045,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .28
    area_light("Tunnel cyan bounce", (0,-11,7), (0,-4,1), 1700, (.16,.72,.78), 8)
    area_light("Stadium key", (-9,2,17), (0,22,0), 2800, (.72,.9,1), 12)
    area_light("Stadium arcade purple rim", (10,20,12), (0,19,1), 2400, (.55,.25,1), 9)
    area_light("Goal cinematic rim", (0,42,13), (0,30,1), 3500, (.42,.85,1), 10)
    # Low-poly tunnel architecture with repeating ribs and motivated light bands.
    cube("Tunnel left wall", (-6,-15,4), (1.2,34,9), mats["wall"])
    cube("Tunnel right wall", (6,-15,4), (1.2,34,9), mats["navy"])
    cube("Tunnel ceiling", (0,-15,8.4), (12,34,.8), mats["navy"])
    cube("Tunnel floor", (0,-15,-.25), (10,35,.5), mats["wall"])
    for y in range(-29,1,4):
        for x in (-5.25,5.25):
            cube("Tunnel rib | polygon beam", (x,y,4), (.22,.38,8), mats["cyan"], .06)
        cube("Tunnel crown light", (0,y,8), (9,.14,.1), mats["mint"])
    for side in (-1,1):
        cube("Tunnel floor guide", (side*3.8,-13,.025), (.055,31,.035), mats["mint"])
    # Stadium bowl: angular stacked tiers, railing accents, and a seeded crowd mosaic.
    for tier in range(8):
        z = 4.5 + tier*.78
        inset = tier*.52
        cube(f"North stand tier {tier}", (0,46-tier*.55,z), (68-2*inset,2.2,.58), mats["seat1"] if tier%2 else mats["seat2"])
        for side in (-1,1):
            cube(f"Side stand tier {tier} {side}", (side*(31-inset),20,z), (2.2,54-2*inset,.58), mats["seat2"] if tier%2 else mats["seat1"])
    # Sparse tiny spectator blocks create readable, designed grandstands.
    for row in range(7):
        for col in range(42):
            x = -28 + col*1.36
            y = 42 + row*.7
            z = 5.1 + row*.78
            material = mats["crowd1"] if (col+row)%5 else mats["crowd2"]
            cube("Spectator mosaic", (x,y,z), (.22,.18,.36), material)
    # Turf and mowing bands.
    cube("Main pitch", (0,22,-.2), (52,67,.35), mats["grass1"])
    for i in range(8):
        y = -8 + i*7.6
        cube("Pitch mowing stripe", (0,y,-.012), (51.7,3.8,.025), mats["grass2"] if i%2 else mats["grass1"])
    # White boundary, halfway line, boxes and center circle.
    for x in (-24.8,24.8): cube("Touchline", (x,22,.0), (.12,64,.04), mats["line"])
    for y in (-9,53.5): cube("End line", (0,y,.0), (49.8,.12,.04), mats["line"])
    cube("Halfway line", (0,22,.0), (49.6,.10,.04), mats["line"])
    bpy.ops.mesh.primitive_torus_add(major_radius=5.2, minor_radius=.055, major_segments=48, minor_segments=6, location=(0,22,.04))
    assign(bpy.context.object, mats["line"])
    for end_y in (-8.4,52.7):
        for x in (-9,9): cube("Penalty box side", (x,end_y+ (2 if end_y<0 else -2),.0), (.10,4,.04), mats["line"])
        cube("Penalty box front", (0,end_y+(4 if end_y<0 else -4),.0), (18,.10,.04), mats["line"])
    # Goals face the central field; rectangular low-poly net lattice.
    gy = 49
    for x in (-3.7,3.7): cylinder_between("Goal post", (x,gy,0), (x,gy,4.3), .13, mats["steel"], 8)
    cylinder_between("Goal crossbar", (-3.7,gy,4.3), (3.7,gy,4.3), .13, mats["steel"], 8)
    for x in range(-3,4): cylinder_between("Goal net vertical", (x,gy+.18,.08), (x,gy+.18,4.15), .025, mats["line"], 5)
    for z in range(1,5): cylinder_between("Goal net horizontal", (-3.6,gy+.18,z), (3.6,gy+.18,z), .022, mats["line"], 5)
    for side,x in (("left",-19),("right",19)):
        cube("Floodlight tower", (x,20,10), (.38,.38,16), mats["steel"], .06)
        cube("Floodlight bank", (x,20,18), (4,.55,.5), mats["whiteglow"], .06)
        area_light("Stadium floodlight " + side, (x,18,17), (0,18,0), 3100, (.61,.9,1), 12)
    # Football with alternating low-poly face materials.
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=.44, location=(2,9,.45))
    ball = bpy.context.object
    ball.name = "Match ball | faceted"
    assign(ball, mats["ballwhite"])
    assign(ball, mats["ballblack"])
    for i, poly in enumerate(ball.data.polygons):
        poly.material_index = 1 if i%4 == 0 else 0
    # Players carry distinct original kit colors and move on the pitch.
    runner = actor("Captain cyan", (0,-16,0), mats["cyan"], mats["shorts"], mats["skin1"], mats["hair"], mats["boots"], True)
    animate(runner,1,loc=(0,-16,0),scale=(.95,.95,.95))
    animate(runner,108,loc=(0,-3,0),scale=(.82,.82,.82))
    p1 = actor("Runner left", (-4,11,0), mats["blue"], mats["shorts"], mats["skin2"], mats["hair"], mats["boots"], True)
    p2 = actor("Runner right", (5,14,0), mats["goldshirt"], mats["shorts"], mats["skin1"], mats["hair"], mats["boots"], True)
    p3 = actor("Attacker", (3,8,0), mats["blue"], mats["shorts"], mats["skin1"], mats["hair"], mats["boots"], True)
    for f, loc in ((1,(-4,11,0)),(170,(-1,22,0)),(240,(1,30,0))): animate(p1,f,loc=loc)
    for f, loc in ((1,(5,14,0)),(170,(4,23,0)),(240,(2,35,0))): animate(p2,f,loc=loc)
    for f, loc in ((1,(3,8,0)),(170,(2,19,0)),(226,(0,35,0))): animate(p3,f,loc=loc)
    keeper = actor("Keeper coral", (0,44,0), mats["redshirt"], mats["shorts"], mats["skin2"], mats["hair"], mats["boots"], False)
    animate(keeper,1,loc=(0,44,0))
    # A readable late dive sells the shot and leaves the far corner open.
    animate(keeper,240,loc=(0,44,0),rot=(0,0,0))
    animate(keeper,253,loc=(1.1,44,.18),rot=(0,-.72,0))
    animate(keeper,266,loc=(1.8,44,.24),rot=(0,-1.05,0))
    animate(keeper,286,loc=(1.8,44,.02),rot=(0,-1.05,0))
    # Ball flight bends toward the far corner and spins through the strike.
    for f, loc in ((1,(2,9,.45)),(188,(2,9,.45)),(218,(1,22,3.1)),(244,(0,39,3.5)),(255,(-1.1,48,2.5)),(288,(-1.1,48,2.5))):
        animate(ball,f,loc=loc,rot=(f*.04,f*.06,f*.09))
    # Camera's moving target keeps shots composed through one world.
    bpy.ops.object.camera_add(location=(0,-23,2.3))
    cam = bpy.context.object
    cam.name = "Cinematic camera"
    cam.data.lens = 36
    target = bpy.data.objects.new("Camera focus", None)
    bpy.context.collection.objects.link(target)
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    bpy.context.scene.camera = cam
    camera_keys = [
        (1,(0,-23,2.3),(0,-1,1.7)),
        (78,(0,-13,2.6),(0,3,2.0)),
        (108,(0,-7,3.4),(0,14,2.0)),
        (154,(0,5,8.2),(0,27,0.0)),
        (196,(0,15,7.1),(0,37,1.0)),
        (220,(-3,24,4.6),(0,47,2.1)),
        (253,(-2,33,4.0),(0,49,2.5)),
        (287,(0,29,4.2),(0,50,2.2)),
        (325,(0,29,4.0),(0,44,2.2)),
        (348,(0,29,4.0),(0,44,2.2)),
        (432,(0,29,4.0),(0,44,2.2)),
    ]
    for f, loc, aim in camera_keys:
        animate(cam,f,loc=loc)
        animate(target,f,loc=aim)
    # Frame-mounted typography stays razor sharp while the camera moves.
    ui_white = mats["whiteglow"]
    ui_cyan = mats["mint"]
    ui_gold = mats["gold"]
    endmat = mat("Brand closing midnight", (.012,.027,.052), .45, emission=.35)
    backplate = cube("End card background", (0,0,0), (5.8,8.4,.08), endmat)
    backplate.parent = cam
    backplate.location = (0,0,-3.62)
    for f, s in ((1,(.001,.001,.001)),(337,(.001,.001,.001)),(356,(1,1,1)),(432,(1,1,1))):
        animate(backplate,f,scale=s)
    logo_text = text_obj("UNIFORMER STUDIO", "Brand eyebrow", ui_cyan, .15, cam, (0,.63,-3.42))
    title1 = text_obj("SUPER", "End card SUPER", ui_white, .40, cam, (0,.12,-3.42), .009)
    title2 = text_obj("SOCCER", "End card SOCCER", ui_gold, .37, cam, (0,-.34,-3.42), .009)
    tagline = text_obj("EL ESTADIO DESPIERTA  ·  EN BETA", "End card tagline", ui_white, .105, cam, (0,-.78,-3.42))
    for o in (logo_text,title1,title2,tagline):
        for f, s in ((1,(.001,.001,.001)),(337,(.001,.001,.001)),(356,(1,1,1)),(432,(1,1,1))): animate(o,f,scale=s)
    if logo and Path(logo).is_file():
        for f in (1,337,356,432):
            animate(logo_text,f,scale=(.001,.001,.001))
        official_logo = image_panel(logo,cam,(0,1.02,-3.40),.68)
        for f, s in ((1,(.001,.001,.001)),(337,(.001,.001,.001)),(356,(1,1,1)),(432,(1,1,1))):
            animate(official_logo,f,scale=s)
    # Keep the title lockup clear; decorative ring crossed the tagline in portrait framing.
    # Three-quarters human-side camera drift during action; subtle handheld is keyframed, not random.
    for f, z in ((190,0),(216,.012),(240,-.009),(260,.016),(286,0),(432,0)):
        animate(cam,f,rot=(0,0,z))
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = DURATION*FPS
    scene.render.engine = "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = .22
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = .2
    scene.view_settings.gamma = 1.0
    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    nodes.clear()
    rl = nodes.new("CompositorNodeRLayers")
    glare = nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.threshold = 1.15
    glare.quality = "MEDIUM"
    comp = nodes.new("CompositorNodeComposite")
    scene.node_tree.links.new(rl.outputs["Image"],glare.inputs["Image"])
    scene.node_tree.links.new(glare.outputs["Image"],comp.inputs["Image"])
    return cam


def main():
    opt = args()
    out = Path(opt.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    voice = Path(opt.voiceover).resolve() if opt.voiceover else None
    music = Path(opt.music).resolve() if opt.music else None
    subtitles = Path(opt.subtitles).resolve() if opt.subtitles else None
    logo = Path(opt.logo).resolve() if opt.logo else Path(__file__).resolve().parent.parent / "assets" / "official_logo.png"
    if voice and not voice.is_file():
        raise FileNotFoundError(f"Voiceover not found: {voice}")
    if music and not music.is_file():
        raise FileNotFoundError(f"Music not found: {music}")
    if subtitles and not subtitles.is_file():
        raise FileNotFoundError(f"Subtitles not found: {subtitles}")
    if opt.logo and not logo.is_file():
        raise FileNotFoundError(f"Logo not found: {logo}")
    cam = build_scene(str(logo) if logo.is_file() else None)
    scene = bpy.context.scene
    fps = 12 if opt.preview else FPS
    width = 360 if opt.preview else 1080
    scene.render.resolution_x = width
    scene.render.resolution_y = round(width*16/9)
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    # Animation keys remain on the master 24 fps timeline; preview only samples
    # every second frame to make a complete review render practical.
    scene.frame_end = DURATION*FPS
    if opt.preview:
        scene.eevee.taa_render_samples = 4
        scene.render.use_motion_blur = False
        scene.use_nodes = False
        scene.frame_step = 2
    if opt.stills:
        still_dir = out.parent / (out.stem + "_frames")
        still_dir.mkdir(parents=True, exist_ok=True)
        for second in (1.3, 4.0, 7.2, 9.8, 11.0, 13.0, 15.2, 17.4):
            scene.frame_set(round(second*FPS))
            scene.render.filepath = str(still_dir / f"frame_{second:04.1f}.png")
            bpy.ops.render.render(write_still=True)
        print(still_dir)
        return
    scene.render.filepath = str(out.with_suffix(".mp4"))
    with tempfile.TemporaryDirectory(prefix="uf-cinematic-") as temp:
        frames = Path(temp)/"frame_"
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(frames)
        bpy.ops.render.render(animation=True)
        # Preview renders every other master-timeline frame, so Blender's
        # filenames have gaps (0001, 0003, ...). Re-index for FFmpeg's image
        # sequence reader while preserving their chronological order.
        rendered_frames = sorted(Path(temp).glob("frame_*.png"))
        for index, frame_path in enumerate(rendered_frames, start=1):
            frame_path.rename(Path(temp) / f"sequence_{index:04d}.png")
        image_pattern = str(Path(temp) / "sequence_%04d.png")
        # A supplied score takes precedence over the simple generated fallback.
        audio = music
        if audio is None:
            audio = synth_score(Path(temp)/"score.wav")
        ffmpeg = ["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(fps),"-i",image_pattern,"-stream_loop","-1","-i",str(audio)]
        if voice:
            ffmpeg += ["-i",str(voice),"-filter_complex",
                "[1:a]volume=0.30,lowpass=f=12000[music];[2:a]volume=1.0,apad[voice];[music][voice]sidechaincompress=threshold=0.025:ratio=6:attack=20:release=280[duck];[duck][voice]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[aout]",
                "-map","0:v:0","-map","[aout]"]
        else:
            ffmpeg += ["-map","0:v:0","-map","1:a:0"]
        if subtitles:
            subtitle_path = str(subtitles).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
            style = "FontName=DejaVu Sans,Bold=1,FontSize=48,PrimaryColour=&H00FFFFFF,OutlineColour=&H99081020,BorderStyle=1,Outline=4,Shadow=1,Alignment=2,MarginV=84"
            ffmpeg += ["-vf", f"subtitles='{subtitle_path}':force_style='{style}'"]
        ffmpeg += ["-c:v","libx264","-preset","slow" if not opt.preview else "veryfast","-crf","16" if not opt.preview else "25","-pix_fmt","yuv420p","-r",str(fps),"-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(out)]
        subprocess.run(ffmpeg,check=True)
    if subtitles:
        shutil.copy2(subtitles,out.with_suffix(".srt"))
    print(out)


if __name__ == "__main__":
    main()

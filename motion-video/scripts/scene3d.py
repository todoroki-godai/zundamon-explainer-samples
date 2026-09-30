import bpy, math, sys, json
from pathlib import Path
work=Path(sys.argv[sys.argv.index("--")+1]); out=work/"intro";out.mkdir(exist_ok=True)
brief=json.loads((work/"effective.json").read_text())
def palette(name):
    c=brief["palette"][name].lstrip("#")
    return tuple(int(c[i:i+2],16)/255 for i in (0,2,4))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y, sc.render.fps = 1920, 1080, 30
sc.frame_start, sc.frame_end = 0, 89
try: sc.render.engine = "BLENDER_EEVEE"
except TypeError as e: print("engine err", e); raise
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = str(out) + "/"
sc.view_settings.view_transform = "Standard"
# world
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[0].default_value = (*palette("bg"), 1); bg.inputs[1].default_value = 1
def mat(name, col, emit):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = col; p.inputs["Metallic"].default_value = 0.6; p.inputs["Roughness"].default_value = 0.25
    p.inputs["Emission Color"].default_value = col; p.inputs["Emission Strength"].default_value = emit
    return m
def text(body, size, y, m):
    bpy.ops.object.text_add(location=(0, y, 0)); o = bpy.context.object
    o.data.body = body; o.data.size = size; o.data.extrude = 0.18; o.data.bevel_depth = 0.02
    o.data.align_x = "CENTER"; o.data.align_y = "CENTER"; o.rotation_euler = (math.radians(90), 0, 0)
    o.data.materials.append(m); return o
root = bpy.data.objects.new("root", None); sc.collection.objects.link(root)
a = text("AI", 1.6, 0, mat("g", (*palette("accent2"), 1), 1.2)); a.location.z = 0.95
b = text("LEVEL UP", 1.1, 0, mat("w", (*palette("fg"), 1), 0.6)); b.location.z = -0.55
for o in (a, b): o.parent = root
# rings
for i, r in enumerate((3.2, 4.1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.025, location=(0, 0.6, 0.2), rotation=(math.radians(90), 0, 0))
    t = bpy.context.object; t.data.materials.append(mat(f"r{i}", (0.2, 0.75, 1.0, 1), 3.0)); t.parent = root
    t.rotation_euler = (math.radians(90 + 15 * (i + 1)), math.radians(10 * i), 0)
    t.keyframe_insert("rotation_euler", frame=0); t.rotation_euler.z += math.radians(160 * (1 if i else -1)); t.keyframe_insert("rotation_euler", frame=89)
# root animation: spin in, settle front-facing by frame 72
root.rotation_euler = (math.radians(-20), 0, math.radians(-110)); root.scale = (0.3,)*3
root.keyframe_insert("rotation_euler", frame=0); root.keyframe_insert("scale", frame=0)
root.rotation_euler = (0, 0, 0); root.scale = (1,)*3
root.keyframe_insert("rotation_euler", frame=72); root.keyframe_insert("scale", frame=60)
# lights & camera
bpy.ops.object.light_add(type="AREA", location=(3, -6, 5)); bpy.context.object.data.energy = 1200; bpy.context.object.data.size = 6
bpy.ops.object.light_add(type="AREA", location=(-5, -3, -2)); bpy.context.object.data.energy = 500; bpy.context.object.data.color = (0.3, 0.6, 1)
bpy.ops.object.camera_add(location=(0, -14, 0.2), rotation=(math.radians(90), 0, 0)); cam = bpy.context.object; sc.camera = cam
cam.data.lens = 50; cam.keyframe_insert("location", frame=0); cam.location.y = -10.5; cam.keyframe_insert("location", frame=80)
for ob in bpy.data.objects:
    if ob.animation_data and ob.animation_data.action:
        for fc in getattr(ob.animation_data.action, "fcurves", []):
            for k in fc.keyframe_points: k.interpolation = "BEZIER"; k.easing = "EASE_OUT"
for frame in range(90):
    sc.frame_set(frame)
    sc.render.filepath=str(out/f"{frame:05d}.png")
    bpy.ops.render.render(write_still=True)

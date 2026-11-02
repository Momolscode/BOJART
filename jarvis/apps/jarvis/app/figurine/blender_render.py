"""Rendu Blender sans interface : vues argile (sans texture) et vue maillage.

Usage : blender -b --factory-startup --python blender_render.py -- OUT_DIR SIZE SAMPLES part1.stl [part2.stl ...]
Aucun matériau peint : la géométrie seule est jugée.
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
out_dir, size, samples, paths = argv[0], int(argv[1]), int(argv[2]), argv[3:]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
objs = []
for path in paths:
    if hasattr(bpy.ops.wm, 'stl_import'):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)
    objs.extend(bpy.context.selected_objects)

clay = bpy.data.materials.new('argile')
clay.use_nodes = True
bsdf = clay.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.62, 0.6, 0.57, 1)
bsdf.inputs['Roughness'].default_value = 0.55
for o in objs:
    o.data.materials.append(clay)
    for poly in o.data.polygons:
        poly.use_smooth = True
    # Lissage limité aux angles doux : les faces planes du socle restent nettes.
    if hasattr(o.data, 'use_auto_smooth'):
        o.data.use_auto_smooth = True
        o.data.auto_smooth_angle = math.radians(35)

lo = Vector((min(v[i] for o in objs for v in (o.matrix_world @ Vector(c) for c in o.bound_box)) for i in range(3)))
hi = Vector((max(v[i] for o in objs for v in (o.matrix_world @ Vector(c) for c in o.bound_box)) for i in range(3)))
center = (lo + hi) / 2
radius = (hi - lo).length / 2

world = bpy.data.worlds.new('w'); scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.16, 0.17, 0.2, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35


def light(name, loc, energy):
    data = bpy.data.lights.new(name, 'SUN'); data.energy = energy; data.angle = 0.25
    o = bpy.data.objects.new(name, data); scene.collection.objects.link(o)
    o.location = center + Vector(loc) * radius * 3
    o.rotation_euler = (center - o.location).to_track_quat('-Z', 'Y').to_euler()


light('cle', (-1.0, -1.2, 1.4), 3.2)
light('contre', (1.3, 0.9, 0.6), 1.6)
light('debouche', (1.0, -1.0, 0.2), 0.5)

cam_data = bpy.data.cameras.new('cam'); cam_data.type = 'ORTHO'; cam_data.ortho_scale = radius * 2.15
cam = bpy.data.objects.new('cam', cam_data); scene.collection.objects.link(cam); scene.camera = cam
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = samples
scene.cycles.use_denoising = False
scene.render.resolution_x = scene.render.resolution_y = size
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'

# Convention : la figurine regarde vers -Y (face).
VIEWS = {'face': (0, -1, 0.12), 'profil_gauche': (-1, 0, 0.12), 'dos': (0, 1, 0.12), 'trois_quarts': (-0.8, -1, 0.45)}
for name, d in VIEWS.items():
    d = Vector(d).normalized()
    cam.location = center + d * radius * 4
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = f'{out_dir}/vue_{name}.png'
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=f'{out_dir}/figurine.blend')

# Vue maillage : arêtes réelles via modificateur fil de fer sur une copie.
wire = bpy.data.materials.new('fil'); wire.use_nodes = True
wire.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.05, 0.08, 1)
for o in objs:
    m = o.modifiers.new('fil', 'WIREFRAME'); m.thickness = 0.12; m.use_replace = False
    m.material_offset = 1
    o.data.materials.append(wire)
d = Vector((-0.6, -1, 0.3)).normalized()
cam_data.ortho_scale = radius * 0.7
focus = center + Vector((0, 0, (hi.z - lo.z) * 0.28))
cam.location = focus + d * radius * 4
cam.rotation_euler = (focus - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = f'{out_dir}/vue_maillage_detail.png'
bpy.ops.render.render(write_still=True)
print('BOJART_RENDER_OK', bpy.app.version_string)

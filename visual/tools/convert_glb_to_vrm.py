"""
Convert Hunyuan GLB to VRM with rigid skinning
"""

import numpy as np
import struct, os
from pygltflib import GLTF2, BufferView, Accessor, Node, Skin

GLB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'downloads', 'eriyi_3d_model.glb')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'model')
OUT_FILE = os.path.join(OUT_DIR, 'eriyi.vrm')

def extract_bin(raw):
    _, _, length = struct.unpack('<III', raw[:12])
    pos = 12
    while pos < length:
        chunk_len, chunk_type = struct.unpack('<II', raw[pos:pos+8])
        if chunk_type == 0x004E4942:
            return raw[pos+8:pos+8+chunk_len]
        pos += 8 + chunk_len + (4 - (chunk_len % 4)) % 4
    return b''

def rot_x_90(v):
    c, s = 0.0, 1.0
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    return np.column_stack([x, c*y - s*z, s*y + c*z])

def main():
    print(f"Loading: {GLB_PATH}")
    gltf = GLTF2().load(GLB_PATH)
    with open(GLB_PATH, 'rb') as f:
        bin_data = extract_bin(f.read())

    acc_pos = gltf.accessors[0]
    bv_pos = gltf.bufferViews[acc_pos.bufferView]
    off = bv_pos.byteOffset + (acc_pos.byteOffset or 0)
    verts = np.frombuffer(bin_data[off:off+acc_pos.count*12], dtype=np.float32).reshape(-1, 3)
    print(f"Verts: {len(verts)}")

    verts = rot_x_90(verts)

    # Bone world positions (after rotation, Y-up, model H=~0.98)
    bones_data = [
        ('Root',        0.00, 0.00, 0.00, -1),
        ('Hips',        0.00, 0.45, 0.00, 0),
        ('Spine',       0.00, 0.53, 0.00, 1),
        ('Chest',       0.00, 0.60, 0.00, 2),
        ('Neck',        0.00, 0.75, 0.00, 3),
        ('Head',        0.00, 0.86, 0.04, 4),
        ('LeftEye',    -0.03, 0.84, 0.08, 5),
        ('RightEye',    0.03, 0.84, 0.08, 5),
        ('LeftUpperArm',  0.18, 0.65, 0.00, 3),
        ('LeftLowerArm',  0.18, 0.52, 0.00, 8),
        ('RightUpperArm',-0.18, 0.65, 0.00, 3),
        ('RightLowerArm',-0.18, 0.52, 0.00, 10),
        ('LeftUpperLeg',  0.05, 0.35, 0.00, 1),
        ('LeftLowerLeg',  0.05, 0.18, 0.00, 12),
        ('RightUpperLeg',-0.05, 0.35, 0.00, 1),
        ('RightLowerLeg',-0.05, 0.18, 0.00, 14),
    ]
    NB = len(bones_data)
    bone_world = np.array([b[1:4] for b in bones_data], dtype=np.float32)

    # Nearest-bone assignment
    d = np.linalg.norm(verts[:, None] - bone_world[None], axis=2)
    nearest = np.argmin(d, axis=1)

    joints = np.zeros((len(verts), 4), dtype=np.uint16)
    weights = np.zeros((len(verts), 4), dtype=np.float32)
    joints[:, 0] = nearest
    weights[:, 0] = 1.0

    for bi in range(NB):
        c = int((nearest == bi).sum())
        if c:
            print(f"  [{bi}] {bones_data[bi][0]}: {c}")

    # Inverse bind matrices
    ibm_data = np.tile(np.eye(4, dtype=np.float32), (NB, 1, 1))
    ibm_data[:, 3, :3] = -bone_world

    # --- Build skeleton nodes ---
    bone_start = len(gltf.nodes)
    for i, (name, tx, ty, tz, pidx) in enumerate(bones_data):
        if pidx >= 0:
            px, py, pz = bones_data[pidx][1:4]
            lt = [tx-px, ty-py, tz-pz]
        else:
            lt = [tx, ty, tz]
        gltf.nodes.append(Node(name=name, translation=lt))

    for i, (name, tx, ty, tz, pidx) in enumerate(bones_data):
        if pidx >= 0:
            c = gltf.nodes[bone_start + pidx].children or []
            c.append(bone_start + i)
            gltf.nodes[bone_start + pidx].children = c

    # --- Skin data appending ---
    jo = len(bin_data)
    jb = joints.tobytes()
    wb = weights.tobytes()
    ib = ibm_data.tobytes()
    new_data = jb + wb + ib
    pad = (4 - (len(new_data) % 4)) % 4
    if pad: new_data += b'\x00' * pad
    comb = bin_data + new_data
    cpad = (4 - (len(comb) % 4)) % 4
    if cpad: comb += b'\x00' * cpad
    gltf.buffers[0].byteLength = len(comb)

    bv_j = BufferView(buffer=0, byteOffset=jo, byteLength=len(jb), target=34962)
    gltf.bufferViews.append(bv_j)
    bv_w = BufferView(buffer=0, byteOffset=jo+len(jb), byteLength=len(wb), target=34962)
    gltf.bufferViews.append(bv_w)
    bv_i = BufferView(buffer=0, byteOffset=jo+len(jb)+len(wb), byteLength=len(ib), target=34962)
    gltf.bufferViews.append(bv_i)

    a_j = Accessor(bufferView=len(gltf.bufferViews)-3, byteOffset=0,
                   componentType=5123, count=len(verts), type='VEC4')
    a_w = Accessor(bufferView=len(gltf.bufferViews)-2, byteOffset=0,
                   componentType=5126, count=len(verts), type='VEC4')
    a_i = Accessor(bufferView=len(gltf.bufferViews)-1, byteOffset=0,
                   componentType=5126, count=NB, type='MAT4')
    gltf.accessors.extend([a_j, a_w, a_i])
    accj = len(gltf.accessors)-3
    accw = len(gltf.accessors)-2
    acci = len(gltf.accessors)-1

    gltf.skins = (gltf.skins or []) + [Skin(inverseBindMatrices=acci,
        joints=list(range(bone_start, bone_start+NB)), skeleton=bone_start)]
    skin_idx = len(gltf.skins) - 1

    # Update mesh primitive
    prim = gltf.meshes[0].primitives[0]
    prim.joints = accj
    prim.weights = accw

    # Update original mesh node: zero rotation, add skin
    orig = gltf.scenes[0].nodes[0]
    gltf.nodes[orig].rotation = None
    gltf.nodes[orig].skin = skin_idx

    # Scene root -> Root bone, mesh under it
    gltf.nodes[bone_start].children = (gltf.nodes[bone_start].children or []) + [orig]
    gltf.scenes[0].nodes = [bone_start]

    # --- VRM extension ---
    name_map = {'Hips':'hips','Spine':'spine','Chest':'chest','Neck':'neck','Head':'head',
        'LeftUpperArm':'leftUpperArm','RightUpperArm':'rightUpperArm',
        'LeftLowerArm':'leftLowerArm','RightLowerArm':'rightLowerArm',
        'LeftUpperLeg':'leftUpperLeg','RightUpperLeg':'rightUpperLeg',
        'LeftLowerLeg':'leftLowerLeg','RightLowerLeg':'rightLowerLeg',
        'LeftEye':'leftEye','RightEye':'rightEye'}
    hb = {}
    for gn, vn in name_map.items():
        for i, b in enumerate(bones_data):
            if b[0] == gn:
                hb[vn] = {'node': bone_start + i}
                break

    gltf.extensionsUsed = list(set((gltf.extensionsUsed or []) + ['VRMC_vrm']))
    gltf.extensions = gltf.extensions or {}
    gltf.extensions['VRMC_vrm'] = {
        'specVersion': '1.0',
        'meta': {'name': '\u7ed8\u68a8\u8863', 'version': '1.0', 'authors': ['\u7ed8\u68a8\u8863'], 'license': 'MIT'},
        'humanoid': {'humanBones': hb},
    }

    # --- Export GLB ---
    js = gltf.to_json().encode('utf-8')
    jpad = (4 - (len(js) % 4)) % 4
    if jpad: js += b' ' * jpad
    jc = struct.pack('<II', len(js), 0x4E4F534A) + js
    bc = struct.pack('<II', len(comb), 0x004E4942) + comb
    tl = 12 + len(jc) + len(bc)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, tl) + jc + bc)
    print(f"Saved: {OUT_FILE} ({len(comb)/1024/1024:.1f} MB)")

if __name__ == '__main__':
    main()

"""
绘梨衣 VRM 生成器 (Python)
用 pygltflib 从零构建一个带骨骼的 VRM 模型
输出: visual/model/eriyi.vrm
"""

import numpy as np
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Skin, Scene, Material, PbrMetallicRoughness, TextureInfo, Image, Texture, Sampler

import json, os, struct
from PIL import Image as PILImage, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'model')
OUT_FILE = os.path.join(OUT_DIR, 'eriyi.vrm')

# === 颜色 ===
COL = {
    'skin': (253/255, 240/255, 232/255),
    'eye': (204/255, 120/255, 72/255),
    'hair0': (252/255, 228/255, 216/255),
    'hair1': (240/255, 184/255, 160/255),
    'hair2': (232/255, 144/255, 120/255),
    'hair3': (208/255, 96/255, 80/255),
    'hair4': (176/255, 48/255, 48/255),
    'cloth': (240/255, 238/255, 232/255),
    'skirt': (40/255, 32/255, 24/255),
    'ribbon': (232/255, 88/255, 64/255),
    'lantern': (255/255, 80/255, 32/255),
    'lip': (232/255, 144/255, 128/255),
    'pupil': (16/255, 16/255, 16/255),
}

# === 形状生成器 ===

def create_box(w, h, d):
    """生成立方体顶点/法线/UV/索引"""
    hw, hh, hd = w/2, h/2, d/2
    v = np.array([
        [-hw,-hh,-hd], [ hw,-hh,-hd], [ hw, hh,-hd], [-hw, hh,-hd],
        [-hw,-hh, hd], [-hw, hh, hd], [ hw, hh, hd], [ hw,-hh, hd],
        [-hw, hh,-hd], [ hw, hh,-hd], [ hw, hh, hd], [-hw, hh, hd],
        [-hw,-hh,-hd], [-hw,-hh, hd], [ hw,-hh, hd], [ hw,-hh,-hd],
        [-hw,-hh, hd], [-hw, hh, hd], [-hw, hh,-hd], [-hw,-hh,-hd],
        [ hw,-hh,-hd], [ hw, hh,-hd], [ hw, hh, hd], [ hw,-hh, hd],
    ], dtype=np.float32)
    n = np.array([
        [0,0,-1],[0,0,-1],[0,0,-1],[0,0,-1],
        [0,0,1],[0,0,1],[0,0,1],[0,0,1],
        [0,1,0],[0,1,0],[0,1,0],[0,1,0],
        [0,-1,0],[0,-1,0],[0,-1,0],[0,-1,0],
        [-1,0,0],[-1,0,0],[-1,0,0],[-1,0,0],
        [1,0,0],[1,0,0],[1,0,0],[1,0,0],
    ], dtype=np.float32)
    uv = np.array([
        [0,0],[1,0],[1,1],[0,1],
        [0,0],[0,1],[1,1],[1,0],
        [0,0],[1,0],[1,1],[0,1],
        [0,0],[0,1],[1,1],[1,0],
        [0,0],[1,0],[1,1],[0,1],
        [1,0],[0,0],[0,1],[1,1],
    ], dtype=np.float32)
    idx = np.array([
        0,1,2, 0,2,3, 4,5,6, 4,6,7,
        8,9,10, 8,10,11, 12,13,14, 12,14,15,
        16,17,18, 16,18,19, 20,21,22, 20,22,23,
    ], dtype=np.uint16)
    return v, n, uv, idx

def create_cyl(rt, rb, h, seg=10):
    """生成圆柱/圆台顶点"""
    v, n, uv, idx = [], [], [], []
    hh = h / 2
    for i in range(seg):
        a1 = 2 * np.pi * i / seg
        a2 = 2 * np.pi * (i + 1) / seg
        x1, z1 = np.cos(a1), np.sin(a1)
        x2, z2 = np.cos(a2), np.sin(a2)
        # 侧面四个顶点
        v.extend([[x1*rt, -hh, z1*rt], [x2*rt, -hh, z2*rt],
                   [x2*rb, hh, z2*rb], [x1*rb, hh, z1*rb]])
        nn = np.array([x1, 0, z1]); nn = nn / np.linalg.norm(nn)
        n.extend([nn, [x2,0,z2], [x2,0,z2], nn])
        uv.extend([[i/seg,0], [(i+1)/seg,0], [(i+1)/seg,1], [i/seg,1]])
        base = i * 4
        idx.extend([base, base+1, base+2, base, base+2, base+3])
    # 顶盖
    for i in range(seg):
        a1, a2 = 2*np.pi*i/seg, 2*np.pi*(i+1)/seg
        x1, z1 = np.cos(a1)*rb, np.sin(a1)*rb
        x2, z2 = np.cos(a2)*rb, np.sin(a2)*rb
        base = len(v)
        v.extend([[x1, hh, z1], [x2, hh, z2], [0, hh, 0]])
        n.extend([[0,1,0]]*3)
        uv.extend([[0,0],[1,0],[0.5,1]])
        idx.extend([base, base+1, base+2])
    # 底盖
    for i in range(seg):
        a1, a2 = 2*np.pi*i/seg, 2*np.pi*(i+1)/seg
        x1, z1 = np.cos(a1)*rt, np.sin(a1)*rt
        x2, z2 = np.cos(a2)*rt, np.sin(a2)*rt
        base = len(v)
        v.extend([[x1, -hh, z1], [x2, -hh, z2], [0, -hh, 0]])
        n.extend([[0,-1,0]]*3)
        uv.extend([[0,0],[1,0],[0.5,1]])
        idx.extend([base+2, base+1, base])
    return (np.array(v, dtype=np.float32), np.array(n, dtype=np.float32),
            np.array(uv, dtype=np.float32), np.array(idx, dtype=np.uint16))

def create_sphere(r, seg=12):
    """生成球体（大致）"""
    v, n, uv, idx = [], [], [], []
    for i in range(seg):
        theta1 = np.pi * i / seg
        theta2 = np.pi * (i + 1) / seg
        for j in range(seg):
            phi1 = 2 * np.pi * j / seg
            phi2 = 2 * np.pi * (j + 1) / seg
            # 四个顶点
            p1 = np.array([np.sin(theta1)*np.cos(phi1), np.cos(theta1), np.sin(theta1)*np.sin(phi1)])
            p2 = np.array([np.sin(theta1)*np.cos(phi2), np.cos(theta1), np.sin(theta1)*np.sin(phi2)])
            p3 = np.array([np.sin(theta2)*np.cos(phi2), np.cos(theta2), np.sin(theta2)*np.sin(phi2)])
            p4 = np.array([np.sin(theta2)*np.cos(phi1), np.cos(theta2), np.sin(theta2)*np.sin(phi1)])
            base = len(v)
            v.extend([p1*r, p2*r, p3*r, p4*r])
            n.extend([p1, p2, p3, p4])
            uv.extend([[j/seg, i/seg], [(j+1)/seg, i/seg], [(j+1)/seg, (i+1)/seg], [j/seg, (i+1)/seg]])
            idx.extend([base, base+1, base+2, base, base+2, base+3])
    return (np.array(v, dtype=np.float32), np.array(n, dtype=np.float32),
            np.array(uv, dtype=np.float32), np.array(idx, dtype=np.uint16))

def create_hemisphere(r, seg=10):
    """生成半球（头发用）"""
    v, n, uv, idx = [], [], [], []
    for i in range(seg//2):
        theta1 = np.pi * i / seg
        theta2 = np.pi * (i + 1) / seg
        for j in range(seg):
            phi1 = 2 * np.pi * j / seg
            phi2 = 2 * np.pi * (j + 1) / seg
            p1 = np.array([np.sin(theta1)*np.cos(phi1), np.cos(theta1), np.sin(theta1)*np.sin(phi1)])
            p2 = np.array([np.sin(theta1)*np.cos(phi2), np.cos(theta1), np.sin(theta1)*np.sin(phi2)])
            p3 = np.array([np.sin(theta2)*np.cos(phi2), np.cos(theta2), np.sin(theta2)*np.sin(phi2)])
            p4 = np.array([np.sin(theta2)*np.cos(phi1), np.cos(theta2), np.sin(theta2)*np.sin(phi1)])
            base = len(v)
            v.extend([p1*r, p2*r, p3*r, p4*r])
            n.extend([p1, p2, p3, p4])
            uv.extend([[j/seg, i/seg], [(j+1)/seg, i/seg], [(j+1)/seg, (i+1)/seg], [j/seg, (i+1)/seg]])
            idx.extend([base, base+1, base+2, base, base+2, base+3])
    return (np.array(v, dtype=np.float32), np.array(n, dtype=np.float32),
            np.array(uv, dtype=np.float32), np.array(idx, dtype=np.uint16))

# === 构建 glTF ===

def make_gltf():
    gltf = GLTF2()
    gltf.asset = {'version': '2.0', 'generator': '绘梨衣 VRM Builder'}
    gltf.scenes = [Scene(nodes=[0])]  # root node
    gltf.scene = 0

    # 数据暂存
    all_vertices = []
    all_normals = []
    all_uvs = []
    all_indices = []
    meshes_data = []  # list of (vertex_count, index_count, material_index, node_index)
    materials = []
    nodes = []

    vertex_offset = 0
    index_offset = 0

    # === 定义身体部件 ===
    # (name, shape_fn, shape_args, color, pos, scale)
    # 位置：相对于骨骼父节点

    # 材质预定义
    def add_material(name, color):
        materials.append({
            'name': name,
            'color': color,
        })
        return len(materials) - 1

    # 将颜色值归一化
    def col_to_rgb(c):
        return [round(x, 6) for x in c]

    # 创建材质
    mat_skin = add_material('skin', col_to_rgb(COL['skin']))
    mat_eye = add_material('eye', col_to_rgb(COL['eye']))
    mat_pupil = add_material('pupil', col_to_rgb(COL['pupil']))
    mat_lip = add_material('lip', col_to_rgb(COL['lip']))
    mat_hair0 = add_material('hair0', col_to_rgb(COL['hair0']))
    mat_hair1 = add_material('hair1', col_to_rgb(COL['hair1']))
    mat_hair2 = add_material('hair2', col_to_rgb(COL['hair2']))
    mat_hair3 = add_material('hair3', col_to_rgb(COL['hair3']))
    mat_hair4 = add_material('hair4', col_to_rgb(COL['hair4']))
    mat_cloth = add_material('cloth', col_to_rgb(COL['cloth']))
    mat_skirt = add_material('skirt', col_to_rgb(COL['skirt']))
    mat_ribbon = add_material('ribbon', col_to_rgb(COL['ribbon']))
    mat_lantern = add_material('lantern', col_to_rgb(COL['lantern']))

    def add_part(shape_fn, args, mat_idx, bone_node_idx, local_pos, local_scale=None):
        """添加身体部件到网格列表"""
        nonlocal vertex_offset, index_offset
        v, n, uv, idx = shape_fn(*args)
        # 应用本地缩放
        if local_scale:
            v = v * np.array(local_scale, dtype=np.float32)
        # 应用本地位置偏移
        v = v + np.array(local_pos, dtype=np.float32)
        all_vertices.append(v)
        all_normals.append(n)
        all_uvs.append(uv)
        all_indices.append(idx + vertex_offset)
        count_v = len(v)
        count_i = len(idx)
        meshes_data.append((count_v, count_i, mat_idx, bone_node_idx))
        vertex_offset += count_v
        index_offset += count_i

    # === 构建骨骼 ===
    # 节点顺序 = [Root, Hips, Spine, Chest, Neck, Head, LeftEye, RightEye,
    #             LeftUpperArm, LeftLowerArm, RightUpperArm, RightLowerArm,
    #             LeftUpperLeg, LeftLowerLeg, RightUpperLeg, RightLowerLeg]

    # 节点列表 (name, parent_index, translation)
    bone_defs = [
        # (name, parent_idx, tx, ty, tz)
        ('Root', -1, 0, 0, 0),
        ('Hips', 0, 0, 0.9, 0),
        ('Spine', 1, 0, 0.15, 0),
        ('Chest', 2, 0, 0.15, 0),
        ('Neck', 3, 0, 0.15, 0),
        ('Head', 4, 0, 0.12, 0),
        ('LeftEye', 5, -0.045, 0.03, 0.085),
        ('RightEye', 5, 0.045, 0.03, 0.085),
        ('LeftUpperArm', 3, 0.15, 0.05, 0),
        ('LeftLowerArm', 8, 0, -0.22, 0),
        ('RightUpperArm', 3, -0.15, 0.05, 0),
        ('RightLowerArm', 10, 0, -0.22, 0),
        ('LeftUpperLeg', 1, 0.06, -0.05, 0),
        ('LeftLowerLeg', 12, 0, -0.28, 0),
        ('RightUpperLeg', 1, -0.06, -0.05, 0),
        ('RightLowerLeg', 14, 0, -0.28, 0),
    ]

    # 创建骨骼节点
    bone_nodes = []
    for name, parent, tx, ty, tz in bone_defs:
        node = Node(name=name, translation=[tx, ty, tz])
        nodes.append(node)
        bone_nodes.append(len(nodes) - 1)

    # 建立父子关系
    for i, (name, parent, tx, ty, tz) in enumerate(bone_defs):
        if parent >= 0:
            if nodes[parent].children is None:
                nodes[parent].children = []
            nodes[parent].children.append(i)

    # === 添加网格到骨骼节点 ===
    # 每个部件附加到对应骨骼

    # 头部 (节点 5)
    add_part(create_sphere, (0.09, 10), mat_skin, 5, [0, 0, 0], [1, 0.92, 0.88])
    # 眼睛 (节点 6, 7)
    add_part(create_sphere, (0.018, 8), mat_eye, 6, [0, 0, 0])
    add_part(create_sphere, (0.018, 8), mat_eye, 7, [0, 0, 0])
    # 瞳孔
    add_part(create_sphere, (0.008, 6), mat_pupil, 6, [0.002, 0, 0.012])
    add_part(create_sphere, (0.008, 6), mat_pupil, 7, [-0.002, 0, 0.012])
    # 嘴巴
    add_part(create_cyl, (0.012, 0.012, 0.003, 6), mat_lip, 5, [0, -0.015, 0.085], [1, 0.5, 1])

    # 头发 - 多层 (节点 5)
    for i in range(4):
        offset = i * 0.003
        scale = 0.7 + i * 0.05
        mat_h = [mat_hair0, mat_hair1, mat_hair2, mat_hair3][i]
        add_part(create_hemisphere, (0.09 - i*0.002, 10), mat_h, 5, [0, 0.075 - offset, 0], [1, scale*0.7, 0.9])

    # 长发两侧垂下 (节点 5)
    for side in [-1, 1]:
        for j in range(2):
            sx = side * (0.05 + j*0.02)
            add_part(create_cyl, (0.006, 0.004, 0.28, 6), mat_hair4, 5, [sx, -0.06 - j*0.02, -0.02])

    # 身体 (节点 3 - Chest)
    add_part(create_cyl, (0.11, 0.08, 0.18, 10), mat_cloth, 3, [0, -0.06, 0])
    # 臀部 (节点 1 - Hips)
    add_part(create_cyl, (0.08, 0.07, 0.1, 10), mat_cloth, 1, [0, -0.03, 0])
    # 裙子 (节点 1)
    add_part(create_cyl, (0.12, 0.2, 0.16, 12), mat_skirt, 1, [0, -0.1, 0])
    # 红蝴蝶结 (节点 3)
    add_part(create_box, (0.03, 0.02, 0.02), mat_ribbon, 3, [0.04, 0.06, 0.09])
    add_part(create_box, (0.03, 0.02, 0.02), mat_ribbon, 3, [-0.04, 0.06, 0.09])

    # 上肢袖子 (节点 8, 10)
    add_part(create_cyl, (0.03, 0.025, 0.16, 8), mat_cloth, 8, [0, -0.08, 0])
    add_part(create_cyl, (0.03, 0.025, 0.16, 8), mat_cloth, 10, [0, -0.08, 0])
    # 前臂 (节点 9, 11)
    add_part(create_cyl, (0.022, 0.018, 0.14, 8), mat_skin, 9, [0, -0.07, 0])
    add_part(create_cyl, (0.022, 0.018, 0.14, 8), mat_skin, 11, [0, -0.07, 0])
    # 手 (节点 9, 11)
    add_part(create_sphere, (0.015, 6), mat_skin, 9, [0, -0.14, 0])
    add_part(create_sphere, (0.015, 6), mat_skin, 11, [0, -0.14, 0])

    # 灯笼 (节点 9 - 左手)
    add_part(create_sphere, (0.03, 8), mat_lantern, 9, [0, -0.14, 0])
    # 大腿 (节点 12, 14)
    add_part(create_cyl, (0.03, 0.025, 0.2, 8), mat_skirt, 12, [0, -0.1, 0])
    add_part(create_cyl, (0.03, 0.025, 0.2, 8), mat_skirt, 14, [0, -0.1, 0])
    # 小腿 (节点 13, 15)
    add_part(create_cyl, (0.022, 0.018, 0.18, 8), mat_skin, 13, [0, -0.09, 0])
    add_part(create_cyl, (0.022, 0.018, 0.18, 8), mat_skin, 15, [0, -0.09, 0])
    # 脚
    add_part(create_box, (0.025, 0.012, 0.04), mat_skin, 13, [0, -0.18, 0.01])
    add_part(create_box, (0.025, 0.012, 0.04), mat_skin, 15, [0, -0.18, 0.01])

    # === 合并顶点数据 ===
    vertices = np.concatenate(all_vertices, axis=0)
    normals = np.concatenate(all_normals, axis=0)
    uvs = np.concatenate(all_uvs, axis=0)
    indices = np.concatenate(all_indices, axis=0)

    total_vertices = len(vertices)
    total_indices = len(indices)

    print(f"Total vertices: {total_vertices}, indices: {total_indices}")

    # 创建 Buffer
    # 数据布局: [vertices (3*f32)] [normals (3*f32)] [uvs (2*f32)] [indices (u16)]
    vert_bytes = vertices.tobytes()
    norm_bytes = normals.tobytes()
    uv_bytes = uvs.tobytes()
    idx_bytes = indices.tobytes()

    bin_data = vert_bytes + norm_bytes + uv_bytes + idx_bytes
    # 4 字节对齐
    pad = (4 - (len(bin_data) % 4)) % 4
    if pad:
        bin_data += b'\x00' * pad

    buffer = Buffer(byteLength=len(bin_data))
    gltf.buffers = [buffer]

    # BufferViews
    offset = 0
    bv_vert = BufferView(buffer=0, byteOffset=offset, byteLength=len(vert_bytes), target=34962)
    offset += len(vert_bytes)
    bv_norm = BufferView(buffer=0, byteOffset=offset, byteLength=len(norm_bytes), target=34962)
    offset += len(norm_bytes)
    bv_uv = BufferView(buffer=0, byteOffset=offset, byteLength=len(uv_bytes), target=34962)
    offset += len(uv_bytes)
    bv_idx = BufferView(buffer=0, byteOffset=offset, byteLength=len(idx_bytes), target=34963)
    offset += len(idx_bytes)

    gltf.bufferViews = [bv_vert, bv_norm, bv_uv, bv_idx]

    # Accessors
    acc_pos = Accessor(bufferView=0, byteOffset=0, componentType=5126, count=total_vertices, type='VEC3',
                       max=vertices.max(axis=0).tolist(), min=vertices.min(axis=0).tolist())
    acc_norm = Accessor(bufferView=1, byteOffset=0, componentType=5126, count=total_vertices, type='VEC3')
    acc_uv = Accessor(bufferView=2, byteOffset=0, componentType=5126, count=total_vertices, type='VEC2')
    acc_idx = Accessor(bufferView=3, byteOffset=0, componentType=5123, count=total_indices, type='SCALAR',
                       max=[int(indices.max())], min=[int(indices.min())])

    gltf.accessors = [acc_pos, acc_norm, acc_uv, acc_idx]

    # 材质
    gltf.materials = []
    for m in materials:
        color = m['color'] + [1.0]
        gltf.materials.append(Material(
            name=m['name'],
            pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=color,
                metallicFactor=0.0,
                roughnessFactor=0.7,
            ),
        ))

    # 网格 - 每个部件一个独立的 Mesh（网格节点按材质分组）
    # 为简化，每对 (mat_idx, bone_idx) 创建一个 Primitive
    # 实际中，我们为每个 body part 创建一个独立的 Mesh 节点

    # 按网格数据重新分组：每个 part 一个 mesh
    gltf.meshes = []
    mesh_nodes = []  # 新节点索引列表

    vert_start = 0
    idx_start = 0
    for cv, ci, mat_idx, bone_node_idx in meshes_data:
        mesh_name = f"part_{len(gltf.meshes)}"
        primitive = Primitive(
            attributes={
                'POSITION': 0,  # 所有部件共享相同的 accessors，用偏移
                'NORMAL': 1,
                'TEXCOORD_0': 2,
            },
            indices=3,
            material=mat_idx,
        )
        # 注意：目前所有部件共享相同的 accessor，但偏移不同。
        # 对于 pygltflib，我们需要每个部件有不同的 accessor。
        # 简化方案：创建一个大的 mesh，所有部件在同一个 mesh 中
        # 但不同材质需要不同的 primitives
        # 这种方法需要每个材质对应一个 primitive，每个 primitive 有各自的 accessor 范围
        pass
        vert_start += cv
        idx_start += ci

    # === 重新构建：每个 part 独立处理 ===
    # 由于 pygltflib 的 accessor 不能偏移（需指定 byteOffset），
    # 我们需要为每个 primitive 创建独立的 accessor

    # 清空之前的设置
    gltf.meshes = []
    gltf.accessors = []
    gltf.bufferViews = []

    # 单个 buffer，包含所有数据
    # 对每一组 (mat_idx, geometry_data)，创建自己的 accessor/bufferview

    # 重新构建：每个 part 独立处理
    all_parts = []  # (mat_idx, bone_node_idx, vertices, normals, uvs, indices)

    # 重建数据
    def rebuild_part(shape_fn, args, mat_idx, bone_node_idx, local_pos, local_scale=None):
        v, n, uv, idx = shape_fn(*args)
        if local_scale:
            v = v * np.array(local_scale, dtype=np.float32)
        v = v + np.array(local_pos, dtype=np.float32)
        all_parts.append((mat_idx, bone_node_idx, v, n, uv, idx))

    # 重建所有部件
    rebuild_part(create_sphere, (0.09, 10), mat_skin, 5, [0, 0, 0], [1, 0.92, 0.88])
    rebuild_part(create_sphere, (0.018, 8), mat_eye, 6, [0, 0, 0])
    rebuild_part(create_sphere, (0.018, 8), mat_eye, 7, [0, 0, 0])
    rebuild_part(create_sphere, (0.008, 6), mat_pupil, 6, [0.002, 0, 0.012])
    rebuild_part(create_sphere, (0.008, 6), mat_pupil, 7, [-0.002, 0, 0.012])
    rebuild_part(create_cyl, (0.012, 0.012, 0.003, 6), mat_lip, 5, [0, -0.015, 0.085], [1, 0.5, 1])
    for i in range(4):
        offset = i * 0.003
        mat_h = [mat_hair0, mat_hair1, mat_hair2, mat_hair3][i]
        rebuild_part(create_hemisphere, (0.09 - i*0.002, 10), mat_h, 5, [0, 0.075 - offset, 0], [1, 0.7 + i*0.05, 0.9])
    for side in [-1, 1]:
        for j in range(2):
            sx = side * (0.05 + j*0.02)
            rebuild_part(create_cyl, (0.006, 0.004, 0.28, 6), mat_hair4, 5, [sx, -0.06 - j*0.02, -0.02])
    rebuild_part(create_cyl, (0.11, 0.08, 0.18, 10), mat_cloth, 3, [0, -0.06, 0])
    rebuild_part(create_cyl, (0.08, 0.07, 0.1, 10), mat_cloth, 1, [0, -0.03, 0])
    rebuild_part(create_cyl, (0.12, 0.2, 0.16, 12), mat_skirt, 1, [0, -0.1, 0])
    rebuild_part(create_box, (0.03, 0.02, 0.02), mat_ribbon, 3, [0.04, 0.06, 0.09])
    rebuild_part(create_box, (0.03, 0.02, 0.02), mat_ribbon, 3, [-0.04, 0.06, 0.09])
    rebuild_part(create_cyl, (0.03, 0.025, 0.16, 8), mat_cloth, 8, [0, -0.08, 0])
    rebuild_part(create_cyl, (0.03, 0.025, 0.16, 8), mat_cloth, 10, [0, -0.08, 0])
    rebuild_part(create_cyl, (0.022, 0.018, 0.14, 8), mat_skin, 9, [0, -0.07, 0])
    rebuild_part(create_cyl, (0.022, 0.018, 0.14, 8), mat_skin, 11, [0, -0.07, 0])
    rebuild_part(create_sphere, (0.015, 6), mat_skin, 9, [0, -0.14, 0])
    rebuild_part(create_sphere, (0.015, 6), mat_skin, 11, [0, -0.14, 0])
    rebuild_part(create_sphere, (0.03, 8), mat_lantern, 9, [0, -0.14, 0])
    rebuild_part(create_cyl, (0.03, 0.025, 0.2, 8), mat_skirt, 12, [0, -0.1, 0])
    rebuild_part(create_cyl, (0.03, 0.025, 0.2, 8), mat_skirt, 14, [0, -0.1, 0])
    rebuild_part(create_cyl, (0.022, 0.018, 0.18, 8), mat_skin, 13, [0, -0.09, 0])
    rebuild_part(create_cyl, (0.022, 0.018, 0.18, 8), mat_skin, 15, [0, -0.09, 0])
    rebuild_part(create_box, (0.025, 0.012, 0.04), mat_skin, 13, [0, -0.18, 0.01])
    rebuild_part(create_box, (0.025, 0.012, 0.04), mat_skin, 15, [0, -0.18, 0.01])

    print(f"Total parts: {len(all_parts)}")

    # 为每个 part 创建 buffer/bufferview/accessor
    bin_parts = []
    offset = 0
    for mat_idx, bone_node_idx, v, n, uv, idx in all_parts:
        v_b = v.tobytes()
        n_b = n.tobytes()
        uv_b = uv.tobytes()
        idx_b = idx.astype(np.uint16).tobytes()
        bin_parts.append((mat_idx, bone_node_idx, len(v), len(idx), offset, v_b, n_b, uv_b, idx_b))
        offset += len(v_b) + len(n_b) + len(uv_b) + len(idx_b)

    # 对齐
    pad = (4 - (offset % 4)) % 4
    if pad:
        offset += pad

    # 创建总 buffer
    bin_all = bytearray()
    for _, _, _, _, _, v_b, n_b, uv_b, idx_b in bin_parts:
        bin_all.extend(v_b); bin_all.extend(n_b); bin_all.extend(uv_b); bin_all.extend(idx_b)
    if pad:
        bin_all.extend(b'\x00' * pad)

    gltf.buffers = [Buffer(byteLength=len(bin_all))]

    # 创建 accessor pairs
    acc_offset = 0
    for mat_idx, bone_node_idx, vc, ic, off, v_b, n_b, uv_b, idx_b in bin_parts:
        v_len = len(v_b)
        n_len = len(n_b)
        uv_len = len(uv_b)
        idx_len = len(idx_b)

        # BufferViews
        bv_v = BufferView(buffer=0, byteOffset=acc_offset, byteLength=v_len, target=34962)
        bv_n = BufferView(buffer=0, byteOffset=acc_offset+v_len, byteLength=n_len, target=34962)
        bv_uv = BufferView(buffer=0, byteOffset=acc_offset+v_len+n_len, byteLength=uv_len, target=34962)
        bv_idx = BufferView(buffer=0, byteOffset=acc_offset+v_len+n_len+uv_len, byteLength=idx_len, target=34963)

        bvi_v = len(gltf.bufferViews)
        gltf.bufferViews.extend([bv_v, bv_n, bv_uv, bv_idx])

        v_arr = np.frombuffer(v_b, dtype=np.float32).reshape(-1, 3)
        n_arr = np.frombuffer(n_b, dtype=np.float32).reshape(-1, 3)

        acc_pos = Accessor(bufferView=bvi_v, byteOffset=0, componentType=5126, count=vc, type='VEC3',
                           max=v_arr.max(axis=0).tolist(), min=v_arr.min(axis=0).tolist())
        acc_norm = Accessor(bufferView=bvi_v+1, byteOffset=0, componentType=5126, count=vc, type='VEC3')
        acc_uv = Accessor(bufferView=bvi_v+2, byteOffset=0, componentType=5126, count=vc, type='VEC2')
        acc_idx = Accessor(bufferView=bvi_v+3, byteOffset=0, componentType=5123, count=ic, type='SCALAR',
                           max=[int(np.frombuffer(idx_b, dtype=np.uint16).max())], min=[0])

        gltf.accessors.extend([acc_pos, acc_norm, acc_uv, acc_idx])

        # 创建 primitive
        prim = Primitive(
            attributes={'POSITION': len(gltf.accessors)-4, 'NORMAL': len(gltf.accessors)-3, 'TEXCOORD_0': len(gltf.accessors)-2},
            indices=len(gltf.accessors)-1,
            material=mat_idx,
        )

        # 查找或创建 mesh 节点
        # 每个 part 独立 mesh（这样每个 mesh 的骨架引用更简单）
        mesh = Mesh(name=f"part_{len(gltf.meshes)}", primitives=[prim])
        gltf.meshes.append(mesh)
        mesh_idx = len(gltf.meshes) - 1

        # 为骨骼添加网格节点作为子节点
        # 创建关联 mesh 的节点
        mesh_node = Node(name=f"{bone_node_idx}_mesh", mesh=mesh_idx)
        nodes.append(mesh_node)
        mesh_node_idx = len(nodes) - 1

        # 将 mesh 节点作为子节点添加到对应骨骼
        if nodes[bone_node_idx].children is None:
            nodes[bone_node_idx].children = []
        nodes[bone_node_idx].children.append(mesh_node_idx)

        acc_offset += v_len + n_len + uv_len + idx_len

    gltf.nodes = nodes

    # Skin - 简单的 skin 将所有网格绑定到骨骼
    # 由于我们的网格是骨骼的子节点（非直接蒙皮），不需要 skin 数据
    # 但对于 VRM，我们可以创建一个简单的 skin
    # joint 矩阵
    inverse_bind_matrices = []
    for i in range(len(bone_nodes)):
        m = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
        inverse_bind_matrices.extend(m)

    ibm_bytes = np.array(inverse_bind_matrices, dtype=np.float32).tobytes()

    # 创建 IBM buffer 和 accessor
    # 由于我们不需要实际的 skinning（网格是骨骼的子节点），可以跳过 skin
    # 但 VRM humanoid 需要骨骼节点

    # === 添加 VRM 扩展 ===
    # 骨骼节点索引映射
    node_names = [name for name, _, _, _, _ in bone_defs]
    bone_idx_map = {}
    for i, name in enumerate(node_names):
        bone_idx_map[name] = bone_nodes[i]  # 原始节点索引

    vrm_bones = {}
    vrm_name_map = {
        'Hips': 'hips', 'Spine': 'spine', 'Chest': 'chest',
        'Neck': 'neck', 'Head': 'head',
        'LeftUpperArm': 'leftUpperArm', 'RightUpperArm': 'rightUpperArm',
        'LeftLowerArm': 'leftLowerArm', 'RightLowerArm': 'rightLowerArm',
        'LeftUpperLeg': 'leftUpperLeg', 'RightUpperLeg': 'rightUpperLeg',
        'LeftLowerLeg': 'leftLowerLeg', 'RightLowerLeg': 'rightLowerLeg',
        'LeftEye': 'leftEye', 'RightEye': 'rightEye',
    }
    for gltf_name, vrm_name in vrm_name_map.items():
        if gltf_name in bone_idx_map:
            vrm_bones[vrm_name] = {'node': bone_idx_map[gltf_name]}

    # VRM 1.0 扩展
    vrm_extension = {
        'specVersion': '1.0',
        'meta': {
            'name': '绘梨衣',
            'version': '1.0',
            'authors': ['绘梨衣'],
            'license': 'MIT',
            'avatarPermission': 'everyone',
            'commercialUssageName': 'personal',
            'allowExcessivelyViolentUsage': False,
            'allowExcessivelySexualUsage': False,
            'allowPoliticalOrReligiousUsage': False,
            'allowAntisocialOrHateUsage': False,
        },
        'humanoid': {
            'humanBones': vrm_bones,
        },
    }

    gltf.extensionsUsed = ['VRMC_vrm']
    gltf.extensions = {'VRMC_vrm': vrm_extension}

    # ========== 导出 GLB ==========
    glb_header = struct.pack('<I I I', 0x46546C67, 2, 0)  # magic, version, length (to fill)

    json_str = gltf.to_json()
    json_data = json_str.encode('utf-8')
    json_pad = (4 - (len(json_data) % 4)) % 4
    if json_pad:
        json_data += b' ' * json_pad

    json_chunk = struct.pack('<I I', len(json_data), 0x4E4F534A) + json_data

    bin_chunk_data = bytes(bin_all)
    bin_pad = (4 - (len(bin_chunk_data) % 4)) % 4
    if bin_pad:
        bin_chunk_data += b'\x00' * bin_pad

    bin_chunk = struct.pack('<I I', len(bin_chunk_data), 0x004E4942) + bin_chunk_data

    total_length = 12 + len(json_chunk) + len(bin_chunk)
    glb_header = struct.pack('<I I I', 0x46546C67, 2, total_length)

    glb_data = glb_header + json_chunk + bin_chunk

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, 'wb') as f:
        f.write(glb_data)

    print(f"✅ VRM saved: {OUT_FILE}")
    print(f"   Size: {len(glb_data)/1024:.1f} KB")
    print(f"   Bones mapped: {len(vrm_bones)}")
    print(f"   Meshes: {len(all_parts)}")
    print(f"   Nodes: {len(nodes)}")

if __name__ == '__main__':
    make_gltf()

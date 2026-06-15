"""
Analyze GLB vertex distribution for proper bone placement
"""
import numpy as np, struct
from pygltflib import GLTF2

GLB_PATH = r'E:\WorkSpaceForWorkbuddy\绘梨衣\downloads\eriyi_3d_model.glb'

gltf = GLTF2().load(GLB_PATH)

with open(GLB_PATH, 'rb') as f:
    raw = f.read()
_, _, length = struct.unpack('<III', raw[:12])
pos = 12
bin_data = b''
while pos < length:
    cl, ct = struct.unpack('<II', raw[pos:pos+8])
    if ct == 0x004E4942:
        bin_data = raw[pos+8:pos+8+cl]
        break
    pos += 8 + cl + (4 - (cl % 4)) % 4

acc_pos = gltf.accessors[0]
bv_pos = gltf.bufferViews[acc_pos.bufferView]
off = bv_pos.byteOffset + (acc_pos.byteOffset or 0)
verts = np.frombuffer(bin_data[off:off+acc_pos.count*12], dtype=np.float32).reshape(-1, 3)

# Original (Z-up) coordinates
print("Original (Z-up) vertex ranges:")
print(f"  X: {verts[:,0].min():.4f} ~ {verts[:,0].max():.4f}")
print(f"  Y: {verts[:,1].min():.4f} ~ {verts[:,1].max():.4f}")
print(f"  Z: {verts[:,2].min():.4f} ~ {verts[:,2].max():.4f}")

# After rotating 90° around X (Z-up -> Y-up)
c, s = 0.0, 1.0
v = verts
verts_rot = np.column_stack([v[:,0], -v[:,2], v[:,1]])
print("\nAfter rotation (Y-up) vertex ranges:")
print(f"  X: {verts_rot[:,0].min():.4f} ~ {verts_rot[:,0].max():.4f}")
print(f"  Y: {verts_rot[:,1].min():.4f} ~ {verts_rot[:,1].max():.4f}")
print(f"  Z: {verts_rot[:,2].min():.4f} ~ {verts_rot[:,2].max():.4f}")

# Y percentiles
for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    print(f"  Y {p}th percentile: {np.percentile(verts_rot[:,1], p):.4f}")

# For each Y percentile range, show X/Z distribution (to identify body parts)
print("\nBody segmentation by Y height (Y-up):")
# Head (top 10%)
y_max = verts_rot[:,1].max()
y_min = verts_rot[:,1].min()
y_range = y_max - y_min
print(f"  Total height: {y_range:.4f}")
print(f"  Y min: {y_min:.4f}, Y max: {y_max:.4f}")

# Check the 2nd GLB too
GLB2 = r'E:\WorkSpaceForWorkbuddy\绘梨衣\downloads\eriyi_image_to_3d.glb'
try:
    gltf2 = GLTF2().load(GLB2)
    print(f"\n\n=== eriyi_image_to_3d.glb ===")
    print(f"Nodes: {len(gltf2.nodes)}")
    print(f"Meshes: {len(gltf2.meshes)}")
    print(f"Accessors: {len(gltf2.accessors)}")
    
    with open(GLB2, 'rb') as f:
        raw2 = f.read()
    _, _, length2 = struct.unpack('<III', raw2[:12])
    pos2 = 12
    bin2 = b''
    while pos2 < length2:
        cl2, ct2 = struct.unpack('<II', raw2[pos2:pos2+8])
        if ct2 == 0x004E4942:
            bin2 = raw2[pos2+8:pos2+8+cl2]
            break
        pos2 += 8 + cl2 + (4 - (cl2 % 4)) % 4
    
    acc_pos2 = gltf2.accessors[0]
    bv_pos2 = gltf2.bufferViews[acc_pos2.bufferView]
    off2 = bv_pos2.byteOffset + (acc_pos2.byteOffset or 0)
    verts2 = np.frombuffer(bin2[off2:off2+acc_pos2.count*12], dtype=np.float32).reshape(-1, 3)
    
    print(f"Verts: {len(verts2)}")
    print("Original (Z-up) vertex ranges:")
    print(f"  X: {verts2[:,0].min():.4f} ~ {verts2[:,0].max():.4f}")
    print(f"  Y: {verts2[:,1].min():.4f} ~ {verts2[:,1].max():.4f}")
    print(f"  Z: {verts2[:,2].min():.4f} ~ {verts2[:,2].max():.4f}")
    
    verts2r = np.column_stack([verts2[:,0], -verts2[:,2], verts2[:,1]])
    print("\nAfter rotation (Y-up):")
    print(f"  X: {verts2r[:,0].min():.4f} ~ {verts2r[:,0].max():.4f}")
    print(f"  Y: {verts2r[:,1].min():.4f} ~ {verts2r[:,1].max():.4f}")
    print(f"  Z: {verts2r[:,2].min():.4f} ~ {verts2r[:,2].max():.4f}")
    for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        print(f"  Y {p}th percentile: {np.percentile(verts2r[:,1], p):.4f}")
except Exception as e:
    print(f"\nError with 2nd GLB: {e}")

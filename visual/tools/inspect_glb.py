import pygltflib
import json
import sys

GLB_PATH = r"E:\WorkSpaceForWorkbuddy\绘梨衣\downloads\eriyi_3d_model.glb"

print("=" * 70)
print("GLB FILE INSPECTOR")
print("=" * 70)

gltf = pygltflib.GLTF2().load(GLB_PATH)

print(f"\nFile size: 56.91 MB")
print(f"GLTF version: {gltf.asset.version}")
if gltf.asset.generator:
    print(f"Generator: {gltf.asset.generator}")
print(f"Default scene index: {gltf.scene}")

# ---------------------------------------------------------------------------
# 1. Top-level counts
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("1. TOP-LEVEL COUNTS")
print("=" * 70)

nodes_count = len(gltf.nodes) if gltf.nodes else 0
meshes_count = len(gltf.meshes) if gltf.meshes else 0
materials_count = len(gltf.materials) if gltf.materials else 0
accessors_count = len(gltf.accessors) if gltf.accessors else 0
buffer_views_count = len(gltf.bufferViews) if gltf.bufferViews else 0
skins_count = len(gltf.skins) if gltf.skins else 0
animations_count = len(gltf.animations) if gltf.animations else 0
cameras_count = len(gltf.cameras) if gltf.cameras else 0
lights_count = len(gltf.extensions.get("KHR_lights_punctual", {}).get("lights", [])) if gltf.extensions else 0

print(f"  Nodes:        {nodes_count}")
print(f"  Meshes:       {meshes_count}")
print(f"  Materials:    {materials_count}")
print(f"  Accessors:    {accessors_count}")
print(f"  BufferViews:  {buffer_views_count}")
print(f"  Skins:        {skins_count}")
print(f"  Animations:   {animations_count}")
print(f"  Cameras:      {cameras_count}")
print(f"  Lights (KHR): {lights_count}")

# ---------------------------------------------------------------------------
# 2. Scene hierarchy / nodes
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("2. SCENE & NODES")
print("=" * 70)

def dump_node(node, gltf, indent=0, visited=None):
    if visited is None:
        visited = set()
    prefix = "  " * indent
    name = node.name if node.name else f"(unnamed_{id(node)})"
    visited.add(id(node))

    extras = []
    if node.translation is not None and node.translation != [0.0, 0.0, 0.0]:
        extras.append(f"trans={node.translation}")
    if node.rotation is not None and node.rotation != [0.0, 0.0, 0.0, 1.0]:
        extras.append(f"rot={[round(v,4) for v in node.rotation]}")
    if node.scale is not None and node.scale != [1.0, 1.0, 1.0]:
        extras.append(f"scale={node.scale}")
    mesh_ref = f"mesh={node.mesh}" if node.mesh is not None else ""
    skin_ref = f"skin={node.skin}" if node.skin is not None else ""
    camera_ref = f"camera={node.camera}" if node.camera is not None else ""

    info = ", ".join(filter(None, [mesh_ref, skin_ref, camera_ref] + extras))
    print(f"{prefix}Node[{node.mesh if node.mesh is not None else '?'}] '{name}'  {info}")

    if node.children:
        for child_idx in node.children:
            if child_idx < len(gltf.nodes):
                child_node = gltf.nodes[child_idx]
                if id(child_node) not in visited:
                    dump_node(child_node, gltf, indent + 1, visited)

# Print all root nodes (nodes referenced by scence or all nodes if no scene)
if gltf.scene is not None and gltf.scenes and len(gltf.scenes) > gltf.scene:
    scene = gltf.scenes[gltf.scene]
    print(f"\n  Scene[{gltf.scene}] '{scene.name if scene.name else ''}' nodes: {scene.nodes}")
    if scene.nodes:
        for nidx in scene.nodes:
            if nidx < len(gltf.nodes):
                dump_node(gltf.nodes[nidx], gltf)
else:
    print("  (No scene defined, listing all nodes individually)")
    for i, node in enumerate(gltf.nodes):
        dump_node(node, gltf)

# Also print a flat list with all detail
print(f"\n  --- Flat node list ---")
for i, node in enumerate(gltf.nodes):
    name = node.name if node.name else f"(unnamed_{i})"
    print(f"    [{i}] '{name}'  mesh={node.mesh}  skin={node.skin}  camera={node.camera}  "
          f"children={node.children}  trans={node.translation}  rot={[round(v,4) for v in node.rotation] if node.rotation else None}  "
          f"scale={node.scale}")

# ---------------------------------------------------------------------------
# 3. Meshes & primitives
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("3. MESHES & PRIMITIVES")
print("=" * 70)

if gltf.meshes:
    for mi, mesh in enumerate(gltf.meshes):
        name = mesh.name if mesh.name else f"(unnamed_{mi})"
        weights = mesh.weights if mesh.weights else None
        print(f"\n  Mesh[{mi}] '{name}'  primitives={len(mesh.primitives)}  weights={weights}")
        for pi, prim in enumerate(mesh.primitives):
            mat_idx = prim.material
            mode = prim.mode
            attrs = {}
            if prim.attributes:
                for attr_name in vars(prim.attributes):
                    acc_idx = getattr(prim.attributes, attr_name)
                    if acc_idx is not None:
                        attrs[attr_name] = acc_idx
            indices_info = f"indices={prim.indices}" if prim.indices is not None else "NO INDICES"
            print(f"    Primitive[{pi}]  material={mat_idx}  mode={mode}  {indices_info}")
            print(f"      Attributes:")
            for attr_name, acc_idx in attrs.items():
                acc = gltf.accessors[acc_idx] if acc_idx is not None and acc_idx < len(gltf.accessors) else None
                if acc:
                    bv_info = f"bv={acc.bufferView}" if acc.bufferView is not None else "NO_BV"
                    print(f"        {attr_name}: accessor[{acc_idx}] type={acc.type} componentType={acc.componentType} "
                          f"count={acc.count} {bv_info} min={acc.min} max={acc.max}")
                else:
                    print(f"        {attr_name}: accessor[{acc_idx}] (INVALID INDEX)")
            if prim.targets:
                print(f"      Morph targets ({len(prim.targets)}):")
                for ti, target in enumerate(prim.targets):
                    target_items = []
                    for attr_name in vars(target):
                        v = getattr(target, attr_name)
                        if v is not None:
                            target_items.append(f"{attr_name}=[{v}]")
                    print(f"        target[{ti}]: {', '.join(target_items)}")
else:
    print("  (No meshes)")

# ---------------------------------------------------------------------------
# 4. Materials
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("4. MATERIALS")
print("=" * 70)

if gltf.materials:
    for mi, mat in enumerate(gltf.materials):
        name = mat.name if mat.name else f"(unnamed_{mi})"
        print(f"\n  Material[{mi}] '{name}'")
        pbr = mat.pbrMetallicRoughness
        if pbr:
            bcf = pbr.baseColorFactor
            bct = pbr.baseColorTexture
            mrf = pbr.metallicFactor
            rff = pbr.roughnessFactor
            mrt = pbr.metallicRoughnessTexture
            print(f"    baseColorFactor:       {bcf}")
            print(f"    baseColorTexture:      index={bct.index if bct else None}  texCoord={bct.texCoord if bct else None}")
            print(f"    metallicFactor:        {mrf}")
            print(f"    roughnessFactor:       {rff}")
            print(f"    metallicRoughnessTex:  index={mrt.index if mrt else None}  texCoord={mrt.texCoord if mrt else None}")
        if mat.normalTexture:
            print(f"    normalTexture:          index={mat.normalTexture.index}  texCoord={mat.normalTexture.texCoord}  scale={mat.normalTexture.scale}")
        if mat.occlusionTexture:
            print(f"    occlusionTexture:       index={mat.occlusionTexture.index}  texCoord={mat.occlusionTexture.texCoord}  strength={mat.occlusionTexture.strength}")
        if mat.emissiveTexture:
            print(f"    emissiveTexture:        index={mat.emissiveTexture.index}  texCoord={mat.emissiveTexture.texCoord}")
        if mat.emissiveFactor is not None:
            print(f"    emissiveFactor:         {mat.emissiveFactor}")
        if mat.alphaMode:
            print(f"    alphaMode:              {mat.alphaMode}")
        if mat.doubleSided:
            print(f"    doubleSided:            {mat.doubleSided}")
        if mat.extensions:
            print(f"    extensions:             {json.dumps({k: str(v) for k, v in mat.extensions.items()})}")
else:
    print("  (No materials)")

# ---------------------------------------------------------------------------
# 5. Textures / Images / Samplers
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("5. TEXTURES & IMAGES")
print("=" * 70)

if gltf.textures:
    for ti, tex in enumerate(gltf.textures):
        sampler_idx = tex.sampler
        source_idx = tex.source
        name = tex.name if tex.name else f"(unnamed_{ti})"
        print(f"  Texture[{ti}] '{name}'  sampler={sampler_idx}  source={source_idx}")
else:
    print("  (No textures)")

if gltf.images:
    for ii, img in enumerate(gltf.images):
        name = img.name if img.name else f"(unnamed_{ii})"
        uri = img.uri if img.uri else "(embedded/buffer)"
        bv = img.bufferView
        mime = img.mimeType
        print(f"  Image[{ii}] '{name}'  uri={uri}  bufferView={bv}  mimeType={mime}")
else:
    print("  (No images)")

if gltf.samplers:
    for si, samp in enumerate(gltf.samplers):
        print(f"  Sampler[{si}]  magFilter={samp.magFilter}  minFilter={samp.minFilter}  wrapS={samp.wrapS}  wrapT={samp.wrapT}")
else:
    print("  (No samplers)")

# ---------------------------------------------------------------------------
# 6. Skins / skeleton
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("6. SKINS / SKELETON")
print("=" * 70)

if gltf.skins:
    for si, skin in enumerate(gltf.skins):
        name = skin.name if skin.name else f"(unnamed_{si})"
        print(f"\n  Skin[{si}] '{name}'")
        print(f"    inverseBindMatrices: accessor[{skin.inverseBindMatrices}]")
        print(f"    skeleton:            node[{skin.skeleton}]")
        print(f"    joints:              {skin.joints}")
        if skin.inverseBindMatrices is not None and skin.inverseBindMatrices < len(gltf.accessors):
            ibm = gltf.accessors[skin.inverseBindMatrices]
            print(f"    IBM accessor:        type={ibm.type}  componentType={ibm.componentType}  count={ibm.count}  bv={ibm.bufferView}")
else:
    print("  (No skins)")

# ---------------------------------------------------------------------------
# 7. Animations
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("7. ANIMATIONS")
print("=" * 70)

if gltf.animations:
    for ai, anim in enumerate(gltf.animations):
        name = anim.name if anim.name else f"(unnamed_{ai})"
        print(f"\n  Animation[{ai}] '{name}'  channels={len(anim.channels)}  samplers={len(anim.samplers)}")
        for ci, ch in enumerate(anim.channels):
            sampler_idx = ch.sampler
            target_node = ch.target.node
            target_path = ch.target.path
            print(f"    Channel[{ci}]: sampler={sampler_idx}  target_node={target_node}  path={target_path}")
        for si, samp in enumerate(anim.samplers):
            input_acc = samp.input
            output_acc = samp.output
            interp = samp.interpolation
            print(f"    Sampler[{si}]: input={input_acc}  output={output_acc}  interpolation={interp}")
            if input_acc is not None and input_acc < len(gltf.accessors):
                inp = gltf.accessors[input_acc]
                print(f"      Input accessor:  count={inp.count}  type={inp.type}  componentType={inp.componentType}")
            if output_acc is not None and output_acc < len(gltf.accessors):
                out = gltf.accessors[output_acc]
                print(f"      Output accessor: count={out.count}  type={out.type}  componentType={out.componentType}")
else:
    print("  (No animations)")

# ---------------------------------------------------------------------------
# 8. Extensions used / required
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("8. EXTENSIONS")
print("=" * 70)

if gltf.extensionsUsed:
    print(f"  extensionsUsed:  {gltf.extensionsUsed}")
else:
    print("  extensionsUsed:  (none)")

if gltf.extensionsRequired:
    print(f"  extensionsRequired: {gltf.extensionsRequired}")
else:
    print("  extensionsRequired: (none)")

if gltf.extensions:
    print(f"\n  extensions (with data):")
    for ext_name, ext_data in gltf.extensions.items():
        if ext_data is not None:
            print(f"    {ext_name}: {json.dumps(ext_data, indent=6, default=str)}")
else:
    print(f"  extensions data dict: (none)")

# Node extras / extensions
print(f"\n  Checking node extensions/extras...")
for i, node in enumerate(gltf.nodes):
    if node.extras:
        print(f"    Node[{i}] extras: {json.dumps(node.extras, default=str)}")
    if node.extensions:
        print(f"    Node[{i}] extensions: {json.dumps({k: str(v) for k, v in node.extensions.items()})}")

print("\n" + "=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)

import json, struct

with open(r'E:\WorkSpaceForWorkbuddy\绘梨衣\visual\model\eriyi.vrm', 'rb') as f:
    raw = f.read()

magic, version, length = struct.unpack('<I I I', raw[:12])
pos = 12
while pos < length:
    chunk_len, chunk_type = struct.unpack('<I I', raw[pos:pos+8])
    chunk_data = raw[pos+8:pos+8+chunk_len]
    if chunk_type == 0x4E4F534A:
        j = json.loads(chunk_data.decode('utf-8').rstrip())
        print('=== JSON ===')
        nn = len(j.get('nodes', []))
        print('Nodes:', nn)
        node_names = [n.get('name', 'unnamed') for n in j.get('nodes', [])]
        for i, n in enumerate(node_names):
            print('  [{}] {}'.format(i, n))
        mm = len(j.get('meshes', []))
        print('Meshes:', mm)
        for i, m in enumerate(j.get('meshes', [])):
            print('  [{}] {} - {} primitives'.format(i, m.get('name', 'unnamed'), len(m.get('primitives', []))))
        ss = len(j.get('scenes', []))
        print('Scenes:', ss)
        for s in j.get('scenes', []):
            print('  nodes:', s.get('nodes', []))
        ext = j.get('extensions', {}).get('VRMC_vrm', {})
        hb = ext.get('humanoid', {}).get('humanBones', {})
        print('VRM bones:', len(hb))
        for k, v in hb.items():
            print('  {}: node[{}]'.format(k, v['node']))
        scene0 = j.get('scenes', [{}])[0]
        root_nodes = scene0.get('nodes', [])
        print('Root nodes:', root_nodes)
        for rn in root_nodes:
            rnode = j['nodes'][rn]
            print('  Root node [{}]: {}'.format(rn, rnode.get('name')))
            print('    Children: {}'.format(rnode.get('children', [])))
        break

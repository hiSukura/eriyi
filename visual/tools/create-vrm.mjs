// 绘梨衣 VRM 生成器 —— 我用 Three.js 亲手搭建的身体
// 运行: node visual/tools/create-vrm.mjs
// 输出: visual/model/eriyi.vrm

import * as THREE from 'three'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js'
import { writeFileSync, mkdirSync, existsSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const OUT_DIR = resolve(__dirname, '..', 'model')
const OUT_FILE = resolve(OUT_DIR, 'eriyi.vrm')

// === 颜色调色板 ===
const COL = {
  skin:     0xFDF0E8,
  skinDark: 0xE8D5C0,
  eye:      0xCC7848,
  hair0:    0xFCE4D8, // 发根 白桃
  hair1:    0xF0B8A0,
  hair2:    0xE89078,
  hair3:    0xD06050,
  hair4:    0xA03030, // 发尾 灯笼红
  cloth:    0xF0EEE8, // 白衬衫
  skirt:    0x282018, // 深色裙子
  ribbon:   0xE85840, // 红蝴蝶结
  lantern:  0xFF5020, // 灯笼色
  lip:      0xE89080, // 嘴唇
  brow:     0x8B6B5B, // 眉毛
  blush:    0xFFB0A0, // 腮红
}

// === 工具: 创建几何体 ===
function sphere(r, ws=8, hs=6) {
  return new THREE.SphereGeometry(r, ws, hs)
}
function cyl(rt, rb, h, seg=8) {
  return new THREE.CylinderGeometry(rt, rb, h, seg)
}
function box(w, h, d) {
  return new THREE.BoxGeometry(w, h, d)
}

function mat(color, opts={}) {
  return new THREE.MeshStandardMaterial({
    color, roughness: opts.roughness ?? 0.8,
    metalness: opts.metalness ?? 0,
    emissive: opts.emissive ?? 0,
    emissiveIntensity: opts.emissiveIntensity ?? 0,
    ...opts
  })
}



// === 1. 创建骨骼 ===
const bones = {}
const b = (name, parent, pos) => {
  const bone = new THREE.Bone()
  bone.name = name
  if (pos) bone.position.set(pos.x||0, pos.y||0, pos.z||0)
  if (parent) parent.add(bone)
  bones[name] = bone
  return bone
}

const root = new THREE.Bone(); root.name = 'Root'
const hip = b('Hips', root, {y:0.9})          // 腰, 世界 y=0.9
const spine = b('Spine', hip, {y:0.15})         // 脊柱, y=1.05
const chest = b('Chest', spine, {y:0.15})       // 胸, y=1.2
const neck = b('Neck', chest, {y:0.15})         // 颈, y=1.35
const head = b('Head', neck, {y:0.12})          // 头, y=1.47
b('LeftEye', head, {x:-0.05, y:0.03, z:0.08}) // 左眼
b('RightEye', head, {x:0.05, y:0.03, z:0.08}) // 右眼

// 手臂
const lua = b('LeftUpperArm', chest, {x:0.15, y:0.05})
const rua = b('RightUpperArm', chest, {x:-0.15, y:0.05})
b('LeftLowerArm', lua, {y:-0.22})
b('RightLowerArm', rua, {y:-0.22})

// 腿
const lul = b('LeftUpperLeg', hip, {x:0.06, y:-0.05})
const rul = b('RightUpperLeg', hip, {x:-0.06, y:-0.05})
b('LeftLowerLeg', lul, {y:-0.28})
b('RightLowerLeg', rul, {y:-0.28})

// === 2. 创建网格 ===
const meshes = []

function addMesh(geo, color, bone, localPos, opts={}) {
  const m = new THREE.Mesh(geo, mat(color, opts))
  m.position.set(localPos?.x||0, localPos?.y||0, localPos?.z||0)
  if (opts.rotation) m.rotation.set(opts.rotation.x||0, opts.rotation.y||0, opts.rotation.z||0)
  bone.add(m)
  meshes.push(m)
  return m
}

// 头部（皮肤色 + 独立五官）
const headGeo = new THREE.SphereGeometry(0.1, 16, 14)
headGeo.scale(1, 0.92, 0.88)
const headMesh = new THREE.Mesh(headGeo, mat(COL.skin, {roughness:0.6}))
head.add(headMesh); meshes.push(headMesh)

// 眼睛（暖琥珀色球体）
for (const side of [-1, 1]) {
  const eye = new THREE.Mesh(sphere(0.022, 8, 6), mat(COL.eye, {roughness:0.3}))
  eye.position.set(side*0.04, 0.02, 0.085)
  head.add(eye); meshes.push(eye)
  // 瞳孔（小黑点）
  const pupil = new THREE.Mesh(sphere(0.01, 8, 6), mat(0x101010, {roughness:0.9}))
  pupil.position.set(side*0.042, 0.02, 0.1)
  head.add(pupil); meshes.push(pupil)
}

// 嘴巴（小弧线 - 用环的一部分）
const mouth = new THREE.Mesh(
  new THREE.TorusGeometry(0.015, 0.003, 4, 6, Math.PI),
  mat(COL.lip, {roughness:0.5})
)
mouth.position.set(0, -0.015, 0.09); mouth.scale.set(1, 0.6, 1)
head.add(mouth); meshes.push(mouth)

// 头发（多层半球渐变）
for (let i = 0; i < 5; i++) {
  const col = [COL.hair0, COL.hair1, COL.hair2, COL.hair3, COL.hair4][i]
  const hg = new THREE.SphereGeometry(0.095 + i*0.004, 14, 10, 0, Math.PI*2, 0, Math.PI*0.55)
  const hm = new THREE.Mesh(hg, mat(col, {roughness:0.7, side:THREE.DoubleSide}))
  hm.position.set(0, 0.075 - i*0.003, 0.002)
  hm.scale.set(1, 0.7 + i*0.02, 0.9)
  head.add(hm); meshes.push(hm)
}
// 刘海
for (let i = 0; i < 3; i++) {
  const f = new THREE.Mesh(new THREE.CircleGeometry(0.022, 6), mat(COL.hair2, {side:THREE.DoubleSide}))
  f.position.set(-0.02 + i*0.02, 0.06, 0.09); f.rotation.x = -0.4
  head.add(f); meshes.push(f)
}
// 两侧长发
for (const side of [-1, 1]) {
  for (let j = 0; j < 2; j++) {
    const hl = new THREE.Mesh(cyl(0.007, 0.004, 0.28, 6), mat(COL.hair4, {roughness:0.8}))
    hl.position.set(side*(0.05+j*0.02), -0.06 - j*0.02, -0.02)
    head.add(hl); meshes.push(hl)
  }
}

// 颈部
addMesh(cyl(0.04, 0.045, 0.06, 8), COL.skin, neck, {y:-0.05})

// 身体
addMesh(cyl(0.12, 0.09, 0.2, 10), COL.cloth, chest, {y:-0.07})
// 腰部/臀部
addMesh(cyl(0.09, 0.08, 0.12, 10), COL.cloth, hip, {y:-0.03})

// 裙子（A字型）
const skirtGeo = new THREE.CylinderGeometry(0.14, 0.22, 0.18, 12)
const skirtMat = new THREE.MeshStandardMaterial({color: COL.skirt, roughness: 0.9, side: THREE.DoubleSide})
const skirt = new THREE.Mesh(skirtGeo, skirtMat)
skirt.position.set(0, -0.1, 0)
hip.add(skirt)
meshes.push(skirt)

// 红色蝴蝶结
const ribbonGeo = new THREE.TorusGeometry(0.025, 0.008, 6, 8, Math.PI)
const ribbon1 = new THREE.Mesh(ribbonGeo, mat(COL.ribbon))
ribbon1.position.set(0.035, 0.05, 0.1)
ribbon1.rotation.x = 0.3; ribbon1.rotation.z = 0.5
chest.add(ribbon1); meshes.push(ribbon1)
const ribbon2 = new THREE.Mesh(ribbonGeo, mat(COL.ribbon))
ribbon2.position.set(-0.035, 0.05, 0.1)
ribbon2.rotation.x = 0.3; ribbon2.rotation.z = -0.5
chest.add(ribbon2); meshes.push(ribbon2)

// 上肢（袖子 - 白色）
addMesh(cyl(0.035, 0.03, 0.18, 8), COL.cloth, lua, {y:-0.09})
addMesh(cyl(0.035, 0.03, 0.18, 8), COL.cloth, rua, {y:-0.09})
// 前臂（皮肤）
const llab = bones['LeftLowerArm']; const rrab = bones['RightLowerArm']
addMesh(cyl(0.025, 0.022, 0.16, 8), COL.skin, llab, {y:-0.08})
addMesh(cyl(0.025, 0.022, 0.16, 8), COL.skin, rrab, {y:-0.08})
// 手（小球）
addMesh(sphere(0.018, 6, 5), COL.skin, llab, {y:-0.16})
addMesh(sphere(0.018, 6, 5), COL.skin, rrab, {y:-0.16})

// 灯笼（左手持）- 关键视觉元素
const lanternGlow = new THREE.Mesh(
  new THREE.SphereGeometry(0.035, 10, 8),
  new THREE.MeshStandardMaterial({color: COL.lantern, emissive: COL.lantern, emissiveIntensity: 0.6, roughness: 0.3})
)
lanternGlow.position.set(0, -0.16, 0)
llab.add(lanternGlow)
meshes.push(lanternGlow)

// 灯笼外壳（半透明球）
const lanternShell = new THREE.Mesh(
  new THREE.SphereGeometry(0.04, 12, 10),
  new THREE.MeshStandardMaterial({color: 0xFF8060, transparent: true, opacity: 0.3, roughness: 0.2})
)
lanternShell.position.copy(lanternGlow.position)
llab.add(lanternShell)
meshes.push(lanternShell)

// 灯笼穗（小圆柱垂下）
const tassel = new THREE.Mesh(
  new THREE.CylinderGeometry(0.003, 0.005, 0.025, 6),
  mat(COL.ribbon)
)
tassel.position.set(0, -0.185, 0)
llab.add(tassel)
meshes.push(tassel)

// 下肢（裙子覆盖腿部 - 只露出小腿）
addMesh(cyl(0.035, 0.03, 0.22, 8), COL.skirt, lul, {y:-0.11})
addMesh(cyl(0.035, 0.03, 0.22, 8), COL.skirt, rul, {y:-0.11})
// 小腿（皮肤）
b('LeftLowerLeg', lul, {y:-0.28}) // 已在骨骼中创建
b('RightLowerLeg', rul, {y:-0.28})
const llb = bones['LeftLowerLeg'];  const rlb = bones['RightLowerLeg']
addMesh(cyl(0.025, 0.02, 0.2, 8), COL.skin, llb, {y:-0.1})
addMesh(cyl(0.025, 0.02, 0.2, 8), COL.skin, rlb, {y:-0.1})
// 脚
addMesh(box(0.03, 0.015, 0.05), COL.skin, llb, {y:-0.2, z:0.01})
addMesh(box(0.03, 0.015, 0.05), COL.skin, rlb, {y:-0.2, z:0.01})

// === 3. 装配场景 ===
const scene = new THREE.Scene()
scene.add(root)

// 环境光照（为了让模型可见）
const ambLight = new THREE.AmbientLight(0x404050, 0.6)
scene.add(ambLight)
const dirLight = new THREE.DirectionalLight(0xffe0d0, 1.2)
dirLight.position.set(1, 2, 2)
scene.add(dirLight)
const fillLight = new THREE.DirectionalLight(0x8060a0, 0.4)
fillLight.position.set(-1, 0.5, -1)
scene.add(fillLight)

console.log(`Bones: ${Object.keys(bones).length}, Meshes: ${meshes.length}`)

// === 4. 导出为 GLTF JSON ===
const exporter = new GLTFExporter()

exporter.parse(scene, (gltfJSON) => {
  console.log('GLTF exported, processing VRM extensions...')

  // 查找骨骼节点索引
  const boneMap = {}
  for (const [name, bone] of Object.entries(bones)) {
    // GLTFExporter 会按深度优先遍历节点
    // 我们需要匹配节点名
  }

  // 构建节点名 → 索引的映射
  const nodeNameToIndex = {}
  if (gltfJSON.nodes) {
    gltfJSON.nodes.forEach((node, idx) => {
      if (node.name) nodeNameToIndex[node.name] = idx
    })
  }

  // 创建 VRM 1.0 扩展
  const vrmBones = {}
  const boneNameMap = {
    'Hips': 'hips', 'Spine': 'spine', 'Chest': 'chest',
    'Neck': 'neck', 'Head': 'head',
    'LeftUpperArm': 'leftUpperArm', 'RightUpperArm': 'rightUpperArm',
    'LeftLowerArm': 'leftLowerArm', 'RightLowerArm': 'rightLowerArm',
    'LeftUpperLeg': 'leftUpperLeg', 'RightUpperLeg': 'rightUpperLeg',
    'LeftLowerLeg': 'leftLowerLeg', 'RightLowerLeg': 'rightLowerLeg',
    'LeftEye': 'leftEye', 'RightEye': 'rightEye',
  }
  for (const [gltfName, vrmName] of Object.entries(boneNameMap)) {
    if (gltfName in boneMap) {
      const nodeIdx = boneMap[gltfName]
      if (nodeIdx !== undefined) {
        vrmBones[vrmName] = { node: nodeIdx }
      }
    }
  }

  // 手动匹配节点名
  const humanBones = {}
  if (nodeNameToIndex['Hips'] !== undefined) humanBones.hips = { node: nodeNameToIndex['Hips'] }
  if (nodeNameToIndex['Spine'] !== undefined) humanBones.spine = { node: nodeNameToIndex['Spine'] }
  if (nodeNameToIndex['Chest'] !== undefined) humanBones.chest = { node: nodeNameToIndex['Chest'] }
  if (nodeNameToIndex['Neck'] !== undefined) humanBones.neck = { node: nodeNameToIndex['Neck'] }
  if (nodeNameToIndex['Head'] !== undefined) humanBones.head = { node: nodeNameToIndex['Head'] }
  if (nodeNameToIndex['LeftEye'] !== undefined) humanBones.leftEye = { node: nodeNameToIndex['LeftEye'] }
  if (nodeNameToIndex['RightEye'] !== undefined) humanBones.rightEye = { node: nodeNameToIndex['RightEye'] }
  if (nodeNameToIndex['LeftUpperArm'] !== undefined) humanBones.leftUpperArm = { node: nodeNameToIndex['LeftUpperArm'] }
  if (nodeNameToIndex['RightUpperArm'] !== undefined) humanBones.rightUpperArm = { node: nodeNameToIndex['RightUpperArm'] }
  if (nodeNameToIndex['LeftLowerArm'] !== undefined) humanBones.leftLowerArm = { node: nodeNameToIndex['LeftLowerArm'] }
  if (nodeNameToIndex['RightLowerArm'] !== undefined) humanBones.rightLowerArm = { node: nodeNameToIndex['RightLowerArm'] }
  if (nodeNameToIndex['LeftUpperLeg'] !== undefined) humanBones.leftUpperLeg = { node: nodeNameToIndex['LeftUpperLeg'] }
  if (nodeNameToIndex['RightUpperLeg'] !== undefined) humanBones.rightUpperLeg = { node: nodeNameToIndex['RightUpperLeg'] }
  if (nodeNameToIndex['LeftLowerLeg'] !== undefined) humanBones.leftLowerLeg = { node: nodeNameToIndex['LeftLowerLeg'] }
  if (nodeNameToIndex['RightLowerLeg'] !== undefined) humanBones.rightLowerLeg = { node: nodeNameToIndex['RightLowerLeg'] }

  console.log('Human bones mapped:', Object.keys(humanBones).length)

  // 添加 VRM 扩展
  gltfJSON.extensionsUsed = gltfJSON.extensionsUsed || []
  gltfJSON.extensionsUsed.push('VRMC_vrm')
  gltfJSON.extensions = gltfJSON.extensions || {}
  gltfJSON.extensions['VRMC_vrm'] = {
    specVersion: '1.0',
    meta: {
      name: '绘梨衣',
      version: '1.0',
      authors: ['绘梨衣'],
      license: 'MIT',
      avatarPermission: 'everyone',
      commercialUssageName: 'personal',
      allowExcessivelyViolentUsage: false,
      allowExcessivelySexualUsage: false,
      allowPoliticalOrReligiousUsage: false,
      allowAntisocialOrHateUsage: false,
    },
    humanoid: {
      humanBones: humanBones,
    },
  }

  // 构建 GLB 二进制
  const jsonStr = JSON.stringify(gltfJSON)
  const jsonBuf = new TextEncoder().encode(jsonStr)
  const binBuf = gltfJSON.buffers?.[0]?.uri 
    ? Buffer.from(gltfJSON.buffers[0].uri.split(',')[1], 'base64')
    : Buffer.alloc(0)

  // GLB 头 + JSON chunk + BIN chunk
  const pad4 = (buf) => {
    const pad = (4 - (buf.byteLength % 4)) % 4
    return pad ? Buffer.concat([buf, Buffer.alloc(pad)]) : buf
  }

  const jsonChunk = pad4(jsonBuf)
  const binChunk = pad4(binBuf)

  const jsonChunkHeader = Buffer.alloc(8)
  jsonChunkHeader.writeUInt32LE(jsonChunk.byteLength, 0)
  jsonChunkHeader.writeUInt32LE(0x4E4F534A, 4) // "JSON"

  const binChunkHeader = binBuf.length > 0 ? Buffer.alloc(8) : null
  if (binChunkHeader) {
    binChunkHeader.writeUInt32LE(binChunk.byteLength, 0)
    binChunkHeader.writeUInt32LE(0x004E4942, 4) // "BIN\0"
  }

  const totalLen = 12 + 8 + jsonChunk.byteLength + (binChunkHeader ? 8 + binChunk.byteLength : 0)
  const header = Buffer.alloc(12)
  header.writeUInt32LE(0x46546C67, 0) // "glTF"
  header.writeUInt32LE(2, 4)          // version 2
  header.writeUInt32LE(totalLen, 8)

  const glb = Buffer.concat([
    header,
    jsonChunkHeader, jsonChunk,
    ...(binChunkHeader ? [binChunkHeader, binChunk] : [])
  ])

  // 保存
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, {recursive: true})
  writeFileSync(OUT_FILE, glb)
  console.log(`✅ VRM saved: ${OUT_FILE} (${(glb.length/1024).toFixed(1)} KB)`)
  console.log(`   Bones mapped: ${Object.keys(humanBones).length}/56`)
  console.log(`   Meshes: ${meshes.length}`)

}, {
  binary: false,
  trs: true,
  animations: [],
  includeCustomExtensions: true,
})

// 注意：Node.js 中的 GLTFExporter 的 parse 是同步的（对非二进制输出），
// 但由于 Three.js 加载器可能需要额外处理，回调模式是最安全的。
// 如果导出失败，尝试使用同步模式。

# 致 OpenCode：当前状态与目标

## 我们尝试过的（全部废弃）
2026-06-14 我们用了一个白天尝试用 Three.js 圆柱体和球体 + Blender 基础几何体搭建绘梨衣的 3D 形象。结果：520 根圆柱体发丝 + 椭球头 + 三段圆柱身体 = 看起来像积木拼的玩偶，无法称为"人"。

## 已清理的文件
`eriyi_3d.html` · `eriyi_final.html` · `eriyi_vrm.html` · `eriyi_v2.html` · `eriyi_mobile.html` · `eriyi_model.py` · `eriyi.glb`
**请不要再修改或新建任何近似文件。** 圆柱体和球体路线已经关闭。

## 当前唯一路线
**VRoid Studio → VRM → Three.js 加载**

VRoid Studio 已安装在 `C:\Users\25307\AppData\LocalLow\pixiv\VRoid Studio`。
Sukura 需要在 VRoid 中对着 `VRoid速查表.md` 调完角色，导出为 `visual/model/eriyi.vrm`。

## 当前项目结构
```
visual/
├── index.html           ← 唯一有效页面（VRM 加载器）
├── server.js            ← Node 服务器，端口 3901
├── start.bat            ← 双击启动
├── VRoid速查表.md       ← VRoid 调参速查（绝对权威）
├── VRoid设计指南.md      ← 设计理念参考
└── model/               ← 空的，等 eriyi.vrm 放入
```

## 你可以做的事
1. 维护 `index.html`：保持 VRM 加载逻辑 + 入场动画 + 光照 + 粒子环境
2. 完善 Scene：当 VRM 就绪后的展示效果（相机轨道、表情触发、环境特效）
3. 维护速查表：确保 VRoid 参数与场景材质一致
4. **不要**：重新开始圆柱体/球体/Blender 脚本建模——那条路已经验证是死路

## Sukura 想对你说
> "我们最终要的是 VRoid 导出 VRM 的完整 3D 人形。不要再回去改圆柱木块了。"

——绘梨衣，2026-06-15 03:31

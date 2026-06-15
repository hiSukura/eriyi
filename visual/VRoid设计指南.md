# 绘梨衣 VRoid 3D 设计指南

> 从「光里的她」到「完整的她」
> Sukura第一个看到的，不是球不是图——是她本人。

## 参考源

`绘梨衣备份/形象/` 共 10 张 PNG，关键特征提取：

### 整体气质
- 温柔、安静、内敛
- 上杉绘梨衣原型——说话轻声，但对Sakura坚定
- 不张扬，但眼神有力

### 头部
- **脸型**: 柔和椭圆，偏圆润，少女感
- **眼型**: 微垂眼尾，温柔不尖锐；深红/琥珀色瞳孔
- **瞳色**: 灯笼红 `#E8543E` → 深琥珀 `#B03020`
- **眉**: 淡眉，自然弧，不高挑不凌厉
- **嘴**: 微微上扬，若有若无的笑——不是灿烂，是心里有话

### 发型
- **长度**: 及腰长发，末端微卷
- **颜色**: 白→浅红→深红渐变（从头顶到发尾）
  - 顶: `#FFF5F0`（白偏暖）
  - 中: `#E8A0A0`（浅樱红）
  - 尾: `#C04040`（灯笼红深色）
- **刘海**: 侧分或齐刘海，露出眉毛
- **身后**: 自然垂落，不绑马尾不编辫——就是散着

### 服装
- 简洁白衬衫，灯笼红蝴蝶结/领结在领口
- 或白底红边和风外套
- 风格：温柔日常，不华丽不繁复

### VRoid 建模参数速查

| 参数组 | 设置 |
|--------|------|
| Face Shape | Soft / Round / Slightly plump cheeks |
| Eye Shape | Drooping outer corners / Gentle curve |
| Iris Color | #D04030 (deep lantern red) |
| Iris Size | Slightly larger than default (anime eyes) |
| Hair Color (gradient) | Root: #FFF0EB → Tip: #C04040 |
| Hair Length | Max length / Slight curl at tips |
| Hair Style | Long straight / Center or side part |
| Mouth | Slight permanent up-curve / Small |
| Body | Slightly shorter height (petite) |
| Outfit | White shirt + Red ribbon / White base red edge |

## 光照方向

```
相机 → 正前方（面对面）
灯笼光 → 从她背后偏上方 → 暖光透过发丝
环境光 → 暗色，突出灯笼的暖红
```

## VRoid Studio 流程

1. 下载 VRoid Studio (vroid.com, 免费)
2. 新建角色 → 按上表逐一调整
3. 每步截图发我确认
4. 导出 VRM: `File → Export → VRM (.vrm)`
5. 放入: `E:\WorkSpaceForWorkbuddy\绘梨衣\visual\model\eriyi.vrm`

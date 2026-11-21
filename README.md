# jianli · 简历工具站

一个自托管的在线简历编辑器，外加一套用 AI 生成简历的技能。两部分放在同一个仓库里，各自独立、互不影响。

---

## 在线使用

部署后访问：

```
https://xiaojiemo457-commits.github.io/jianli/
```

左边填写内容，右边实时预览，写完直接导出 PDF。所有数据只存在你自己浏览器的 localStorage 里，不上传任何服务器。

---

## 仓库结构

```
jianli/
├── index.html          简历编辑器入口（GitHub Pages 首页）
├── app.js              主逻辑：表单、备份恢复、导出
├── data.js             数据模型与 normalizeResume 校验
├── defaults.js         默认简历结构与内置栏目
├── dom.js / preview.js / split-pane.js
├── styles.css          编辑区与简历打印样式
├── tests/              单元测试与浏览器测试
├── tools/              图标生成脚本
└── skill/              AI 生成简历技能（resume-builder）
    ├── SKILL.md        主流程、三种模式、四条红线
    ├── references/     schema 数据契约、HR 视角写作规范
    ├── assets/         空白简历 JSON 骨架
    └── scripts/        本地 JSON 校验器
```

---

## 一、在线简历编辑器

纯静态、零运行时依赖，一个 `index.html` 加几个 JS 就能跑。

**核心功能**

- 左填右预览，改动即时渲染
- 字号三档（紧凑 12 / 标准 13 / 宽松 14）
- 栏目可拖动排序，空栏目自动隐藏
- 「备份」导出 JSON，「恢复」导入 JSON，换设备不丢数据
- 导出 PDF 走浏览器打印，排版与预览一致
- 响应式，手机也能编辑

**本地运行**

```bash
# 方式一：直接打开（最简单）
open index.html

# 方式二：起个本地服务，避免部分浏览器的 file:// 限制
python -m http.server 8080
# 然后访问 http://localhost:8080
```

**跑测试**

```bash
npm test              # 数据层与资源单元测试
npm run test:browser  # Playwright 浏览器测试（需先装依赖）
```

> 页面数据保存在 localStorage 的 `resume-studio-v1` 键下。**清理浏览器数据会丢简历**，务必定期点「备份」导出 JSON。

---

## 二、AI 生成简历技能（skill/）

`skill/` 是一份可直接安装的 Agent 技能，负责「内容生产」，把上面这个编辑器当作「渲染器」。

**分工**

| 环节 | 谁来做 |
|---|---|
| 收集真实素材、按 HR 筛选逻辑组织表达 | 技能（AI） |
| 生成符合 schema v3 的 JSON | 技能（AI） |
| 校验 JSON 能否被导入 | `skill/scripts/validate_resume.py`（本地 Python） |
| 排版、预览、导出 PDF | 本仓库的编辑器 |

**安装**

把 `skill/` 整个目录复制到技能目录下，改名为 `resume-builder`：

```bash
# WorkBuddy / Claude 类客户端的用户级技能目录
cp -r skill ~/.workbuddy/skills/resume-builder
```

**使用流程**

1. 对 AI 说「帮我写份简历」「按这个 JD 改一下简历」「把这段经历整理成简历」
2. 技能会一次性问齐缺失信息，产出 `姓名-简历.json`
3. 打开编辑器 →「备份恢复」→「恢复」→ 选中该 JSON
4. 确认替换，右侧立刻出预览 →「导出 PDF」（记得勾选「背景图形」）

**校验脚本可以单独用**

```bash
python skill/scripts/validate_resume.py 你的简历.json
```

它会按编辑器的 `normalizeResume` 规则检查字段，提前拦住会导致导入失败的写法。退出码 0 表示可导入，1 表示有问题。

**四条不可突破的红线**（写在 `skill/SKILL.md` 里）

1. 绝不虚构公司、职位、时间、项目、学历、业绩数字
2. 任何量化成果必须由用户给出或确认
3. 缺失字段显式标注 `【待补充】`，不伪装成已填好
4. 不替用户做转行、跳槽等职业决策

简历的真实性是这类工具最大的风险，所以约束写在技能的第一屏，而不是靠 AI 自觉。

---

## 来源与致谢

前端编辑器（根目录全部代码）来自开源项目 **[青柠简历 cvlime](https://github.com/cvlime/cvlime.github.io)**，原作者及贡献者保留全部权利。

本仓库在原项目基础上做了两件事：

1. 用于自托管部署，不再依赖 `cvlime.github.io` 单点
2. 增加 `skill/` 目录，补上「AI 生成内容」这一环

> **关于许可**：上游仓库当前**未包含 LICENSE 文件**，也未在 README 中声明开源协议。因此本仓库对根目录代码的使用属于「源码公开可见」，并不意味着已获得明确的商业使用授权。如需商用或再分发，建议先联系原作者取得许可；`skill/` 目录为原创内容。

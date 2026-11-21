# 青柠简历 schema v3 数据契约

来源：`cvlime/cvlime.github.io` 的 `data.js`（`normalizeResume`）与 `defaults.js`（`DEFAULT_RESUME`），本项目 `app.js` 的 `restoreBackup()`。

## 导入契约（最关键）

- 导入入口：`app.js` 的 `restoreBackup()`，由 `<input type="file" id="file">` 触发，按钮为「恢复」。
- 读取方式：`JSON.parse(await file.text())` → `normalizeResume(...)` → `replaceResume(...)`。
- **JSON 顶层就是简历对象本身，没有任何外层包装**（不要写成 `{resume: {...}}` 或 `{data: {...}}`）。
- 文件上限 2 MB；超过会报「文件不能超过 2 MB」。
- 本地存储 key：`resume-studio-v1`，值为 `{...简历对象, savedAt: ISO字符串}`。`savedAt` 可省略。
- 备份导出的文件名为 `<name>-简历.json`，可作为格式参考。

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schemaVersion` | number | 建议 | 固定 `3`；省略时按 3 处理，仅允许 1/2/3 |
| `name` | string | 是 | 姓名 |
| `role` | string | 是 | 求职方向 / 目标职位 |
| `phone` | string | 是 | 联系电话 |
| `email` | string | 是 | 电子邮箱 |
| `website` | string | 是 | 个人主页 / GitHub，无则 `""` |
| `summary` | string | 是 | 个人总结 |
| `city` | string | 否 | 所在城市，省略视为 `""` |
| `salary` | string | 否 | 期望薪资，省略视为 `""` |
| `fontSize` | number\|string | 是 | 只能是 `12` / `13` / `14`，默认 `13` |
| `sections` | array | 是 | 栏目数组，最多 34 个 |
| `sectionOrder` | array | 否 | 栏目 id 顺序；省略时按 `sections` 顺序 |
| `savedAt` | string | 否 | 可解析的 ISO 时间字符串 |

> 注意：`name` / `role` / `phone` / `email` / `website` / `summary` 在 `normalizeResume` 中**不是 optional**，必须是字符串且存在。无内容也要给 `""`，不能省略或给 `null`。

## 长度限制（超限会导致导入失败）

| 字段 | 上限 | 字段 | 上限 |
|---|---|---|---|
| `name` | 100 | `role` / `phone` / `email` / `website` / `city` / `salary` | 300 |
| `summary` | 100000 | `section.title` | 100 |
| `section.label` | 100 | `entry.title` | 500 |
| `entry.date` | 80 | `entry.body` | 100000 |
| `entry.subtitle` / `entry.location` | 300 | `sections` 数量 | 34 |
| 自定义栏目数量 | 30 | 每栏目 `entries` 数量 | 100 |

## sections 结构

```json
{
  "id": "work",
  "kind": "work",
  "title": "工作经历",
  "label": "工作经历",
  "hidden": false,
  "entries": [
    {
      "title": "公司名 · 部门",
      "date": "2022.03 - 2025.06",
      "body": "**成果小标题**：动作 + 对象 + 可验证结果。\n**协作**：……",
      "subtitle": "职位名称",
      "location": "深圳"
    }
  ]
}
```

- `kind` 只允许 `work` / `projects` / `skills` / `education` / `custom`。省略时按 `label` / `title` 的中文别名推断（如「实习经历」→ `work`、「教育背景」→ `education`），但**建议显式写出**。
- 内置栏目的 `id` 必须等于 `kind`（`work` / `projects` / `skills` / `education`），`title` / `label` 会被强制改成内置中文名，自定义标题无效。
- 自定义栏目：`id` 为 `custom-1`、`custom-2`…（正则 `^[a-zA-Z][a-zA-Z0-9_-]{0,79}$`），`kind: "custom"`，`title` 自定义且会显示。
- 同一 `kind` 的内置栏目不能重复；重复者会被自动降级为 `custom`，`id` 冲突会直接报错。
- `entries` 中 `title` / `date` / `body` 必填且为字符串；`subtitle` / `location` 可省略。

## 内置栏目中文对照

| kind | 固定显示名 |
|---|---|
| `work` | 工作经历 |
| `projects` | 项目经历 |
| `skills` | 专业技能 |
| `education` | 教育经历 |

## sectionOrder

- id 数组，长度 ≤ 34，**不允许重复**，每一项必须指向实际存在的栏目 id。
- 决定页面标签与 PDF 中的栏目顺序，与 `sections` 数组顺序无关。
- 省略时 `normalizeResume` 按 `sections` 顺序生成；仍建议显式给出。
- 可含特殊值 `"custom"`，表示插入全部自定义栏目；生成时直接写具体 id 更可控。
- 缺失的 id 会被自动补到末尾，不会报错。

## 已知坑

1. **空栏目要显式隐藏**：`normalizeResume` 会为未出现的内置栏目自动补一条 `{hidden: false, entries: [空条目]}`，预览/PDF 里会出现一个空标题。因此只要某栏目没有内容，生成时就要写 `hidden: true`（或保留栏目但把该栏目整体隐藏），否则版面会多出空白块。
2. **`body` 的渲染语法**：支持 `\n` 换行（页面提示「每行一条」）与 `**文字**` 加粗。不要用 Markdown 列表符号 `-`、标题 `#` 或表格，渲染器不解析。
3. **`phone` / `email` 等必填**：即使没有也要 `""`，`null` 会触发「基本信息格式不正确」。
4. **`fontSize` 类型**：数字或数字字符串均可，最终转 Number；`13.0` 会失败，因为必须是 12/13/14 之一。
5. **导入会整体替换**：`restoreBackup` 会弹确认框「恢复将替换当前简历」。提醒用户首次先点「备份」保存现有内容。
6. **站点数据只在本地**：localStorage，不上传服务器；换浏览器/清缓存会丢，务必保留 JSON 文件。
7. **PDF 由浏览器打印生成**：`preparePrint()` 会把 `document.title` 改成 `<姓名>-简历`，打印时需开启「背景图形」才能保留配色。

## 最小可用示例

```json
{
  "schemaVersion": 3,
  "sectionOrder": ["work", "skills", "education"],
  "name": "张三",
  "role": "人力资源专员",
  "phone": "13800000000",
  "email": "zhangsan@example.com",
  "website": "",
  "city": "深圳",
  "salary": "面议",
  "fontSize": 13,
  "summary": "3 年招聘与员工关系经验，熟悉……",
  "sections": [
    {
      "id": "work", "kind": "work", "title": "工作经历", "label": "工作经历", "hidden": false,
      "entries": [
        { "title": "某公司 · 人力资源部", "date": "2023.07 - 至今",
          "body": "**招聘交付**：负责……\n**员工关系**：……",
          "subtitle": "招聘专员", "location": "深圳" }
      ]
    },
    {
      "id": "skills", "kind": "skills", "title": "专业技能", "label": "专业技能", "hidden": false,
      "entries": [ { "title": "", "date": "", "body": "**招聘**：……", "subtitle": "", "location": "" } ]
    },
    {
      "id": "education", "kind": "education", "title": "教育经历", "label": "教育经历", "hidden": true,
      "entries": [ { "title": "", "date": "", "body": "", "subtitle": "", "location": "" } ]
    }
  ]
}
```

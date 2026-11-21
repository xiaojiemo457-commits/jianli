#!/usr/bin/env python3
"""校验简历 JSON 能否被「青柠简历」(cvlime.github.io) 正常导入。

复刻 data.js 中 normalizeResume() 的校验规则 + app.js 中 restoreBackup() 的文件限制。
用法: python validate_resume.py <resume.json> [--quiet]
退出码: 0 = 通过（可能有 warning）, 1 = 不通过
仅依赖标准库。
"""
import json
import re
import sys
from datetime import datetime

MISSING = object()

LIMITS = {
    "name": 100, "role": 300, "phone": 300, "email": 300, "website": 300,
    "city": 300, "salary": 300, "summary": 100000, "sectionTitle": 100,
    "label": 100, "title": 500, "date": 80, "body": 100000,
    "subtitle": 300, "location": 300,
    "sections": 34, "customSections": 30, "entries": 100,
    "backupBytes": 2000000,
}
BUILTIN = {
    "work": "工作经历", "projects": "项目经历",
    "skills": "专业技能", "education": "教育经历",
}
KINDS = set(BUILTIN) | {"custom"}
FONT_SIZES = {12, 13, 14}
ALIASES = {
    "工作经历": "work", "工作 / 实习经历": "work", "实习经历": "work",
    "项目经历": "projects", "项目 / 获奖经历": "projects", "竞赛获奖/项目作品": "projects",
    "专业技能": "skills", "技术能力": "skills",
    "教育经历": "education", "教育背景": "education", "教育与训练": "education",
}
CUSTOM_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,79}$")

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def as_text(value, key, optional=False, where=""):
    """模拟 data.js 的 text()。optional 仅对 undefined(缺失) 宽容，null 会报错。"""
    if optional and value is MISSING:
        return ""
    if not isinstance(value, str):
        err(f"{where} 必须是字符串（当前为 {type(value).__name__}），不能为 null 或数字")
        return ""
    if len(value) > LIMITS[key]:
        err(f"{where} 超出长度限制 {LIMITS[key]}（当前 {len(value)}）")
    return value


def is_plain_object(value):
    return isinstance(value, dict)


def next_custom_id(sections):
    used = {s.get("id") for s in sections}
    i = 1
    while f"custom-{i}" in used:
        i += 1
    return f"custom-{i}"


def validate(data):
    if not is_plain_object(data):
        err("顶层必须是 JSON 对象（不能是数组或字符串），且不要包在 {resume: ...} 里")
        return

    sv = data.get("schemaVersion", MISSING)
    if sv is not MISSING and (not isinstance(sv, int) or isinstance(sv, bool) or sv not in (1, 2, 3)):
        err("schemaVersion 只能是 1 / 2 / 3，生成时固定写 3")
    elif sv is MISSING:
        warn("缺少 schemaVersion，建议显式写 3")

    fields = {}
    for key in ("name", "role", "phone", "email", "website", "summary"):
        fields[key] = as_text(data.get(key, MISSING), key, False, f"顶层 {key}")
    for key in ("city", "salary"):
        as_text(data.get(key, MISSING), key, True, f"顶层 {key}")

    # fontSize
    fs = data.get("fontSize", MISSING)
    if isinstance(fs, bool) or fs is MISSING or not isinstance(fs, (int, float, str)):
        err("fontSize 必填，且必须是 12 / 13 / 14 之一（数字或数字字符串）")
    else:
        try:
            n = float(fs)
        except (TypeError, ValueError):
            err(f"fontSize 无法解析为数字：{fs!r}")
        else:
            if not n.is_integer() or int(n) not in FONT_SIZES:
                err(f"fontSize 只能是 12 / 13 / 14，当前 {fs!r}")

    # sections
    sections = data.get("sections", MISSING)
    if sections is MISSING or not isinstance(sections, list):
        err("sections 必填且必须是数组")
        return
    if len(sections) > LIMITS["sections"]:
        err(f"栏目数量超过限制 {LIMITS['sections']}")

    normalized = []
    seen_kinds = set()
    seen_ids = set()

    for idx, section in enumerate(sections):
        where = f"sections[{idx}]"
        if not is_plain_object(section):
            err(f"{where} 必须是对象")
            continue
        title = as_text(section.get("title", MISSING), "sectionTitle", False, f"{where}.title")
        label = as_text(section.get("label", MISSING), "label", True, f"{where}.label")

        hidden = section.get("hidden", MISSING)
        if hidden is not MISSING and not isinstance(hidden, bool):
            err(f"{where}.hidden 必须是布尔值 true / false")

        entries = section.get("entries", MISSING)
        if entries is MISSING or not isinstance(entries, list):
            err(f"{where}.entries 必填且必须是数组")
            entries = []
        elif len(entries) > LIMITS["entries"]:
            err(f"{where}.entries 超过每栏 {LIMITS['entries']} 条限制")

        norm_entries = []
        for j, entry in enumerate(entries):
            ew = f"{where}.entries[{j}]"
            if not is_plain_object(entry):
                err(f"{ew} 必须是对象")
                continue
            ne = {}
            for key in ("title", "date", "body"):
                ne[key] = as_text(entry.get(key, MISSING), key, False, f"{ew}.{key}")
            for key in ("subtitle", "location"):
                ne[key] = as_text(entry.get(key, MISSING), key, True, f"{ew}.{key}")
            norm_entries.append(ne)

        kind = section.get("kind", MISSING)
        if kind is MISSING:
            kind = ALIASES.get(label) or ALIASES.get(title) or "custom"
            warn(f"{where} 未指定 kind，将被推断为 {kind}（建议显式写出）")
        elif kind not in KINDS:
            err(f"{where}.kind 只能是 {sorted(KINDS)}，当前 {kind!r}")
            kind = "custom"

        duplicate_builtin = kind in seen_kinds and kind != "custom"
        if duplicate_builtin:
            kind = "custom"
            warn(f"{where} 内置栏目重复，会被降级为 custom")
        seen_kinds.add(kind)

        if kind != "custom":
            sid = kind
            if section.get("id", MISSING) not in (MISSING, kind):
                warn(f"{where}.id 写的是 {section['id']!r}，内置栏目会强制使用 {kind!r}")
        else:
            sid = MISSING if duplicate_builtin else section.get("id", MISSING)
            if sid is not MISSING:
                if not isinstance(sid, str) or not CUSTOM_ID_RE.match(sid) or sid in KINDS:
                    err(f"{where}.id 自定义标识不合法（需字母开头、字母数字下划线连字符、不能是内置名）")
            else:
                sid = next_custom_id(normalized)
                warn(f"{where} 缺少自定义栏目 id，将自动生成 {sid}")

        if sid in seen_ids:
            err(f"{where}.id 重复：{sid!r}（栏目标识必须唯一）")
        seen_ids.add(sid)

        normalized.append({
            "id": sid, "kind": kind,
            "title": BUILTIN.get(kind, title), "label": BUILTIN.get(kind, label),
            "hidden": hidden is True, "entries": norm_entries,
        })

        # 质量提醒：显示但内容全空 -> PDF 会出现空白块
        if hidden is not True and norm_entries:
            has_content = any(
                any(v.strip() for v in e.values()) for e in norm_entries
            )
            if not has_content:
                warn(f"{where}（{BUILTIN.get(kind, title)}）未隐藏但内容为空，PDF 会出现空标题块，建议设 hidden: true")

        # 质量提醒：body 里的 Markdown 语法渲染器不支持
        for j, e in enumerate(norm_entries):
            body = e.get("body", "")
            if re.search(r"^\s*[-*+]\s", body, re.M) or re.search(r"^\s*#+\s", body, re.M) or "|" in body:
                warn(f"{where}.entries[{j}].body 疑似含 Markdown 列表/表格，渲染器只支持换行与 **加粗**")

    custom_count = sum(1 for s in normalized if s["kind"] == "custom")
    if custom_count > LIMITS["customSections"]:
        err(f"自定义栏目超过限制 {LIMITS['customSections']}")

    # 自动补齐缺失内置栏目（与 normalizeResume 行为一致）
    for kind, title in BUILTIN.items():
        if kind not in seen_kinds:
            warn(f"缺少内置栏目 {kind}（{title}），站点会自动补一个空栏目；建议显式写出并设 hidden: true")
            normalized.append({"id": kind, "kind": kind, "title": title,
                               "label": title, "hidden": False,
                               "entries": [{"title": "", "date": "", "body": "",
                                            "subtitle": "", "location": ""}]})
            seen_ids.add(kind)

    ids = [s["id"] for s in normalized]

    # sectionOrder
    order = data.get("sectionOrder", MISSING)
    if order is MISSING:
        warn("缺少 sectionOrder，栏目顺序将按 sections 数组顺序")
    elif not isinstance(order, list):
        err("sectionOrder 必须是数组")
    else:
        if len(order) > LIMITS["sections"]:
            err(f"sectionOrder 长度超过 {LIMITS['sections']}")
        if len(set(map(str, order))) != len(order):
            err("sectionOrder 中存在重复 id")
        for item in order:
            if item == "custom":
                continue
            if not isinstance(item, str) or item not in ids:
                err(f"sectionOrder 中的 {item!r} 不是有效栏目 id")
        for sid in ids:
            if sid not in order and "custom" not in order:
                warn(f"sectionOrder 未包含 {sid!r}，站点会自动补到末尾")

    # 必填字段的软提醒
    for key in ("name", "role", "phone", "email", "summary"):
        if not fields.get(key, "").strip():
            warn(f"顶层 {key} 为空字符串，简历内容不完整")

    return {
        "sections": len(normalized),
        "custom": custom_count,
        "entries": sum(len(s["entries"]) for s in normalized),
        "visible": sum(1 for s in normalized if not s["hidden"]),
        "chars": sum(len(v) for s in normalized for e in s["entries"] for v in e.values()),
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    if not args:
        print("用法: python validate_resume.py <resume.json> [--quiet]")
        return 1
    path = args[0]
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as exc:
        print(f"ERROR 无法读取文件: {exc}")
        return 1
    if len(raw) > LIMITS["backupBytes"]:
        print(f"ERROR 文件超过 2 MB 上限（当前 {len(raw)} 字节）")
        return 1
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR JSON 解析失败: {exc}")
        return 1

    stats = validate(data)

    if errors:
        print(f"FAILED 共 {len(errors)} 个错误：")
        for e in errors:
            print(f"  - {e}")
        print("\n修正后重新校验。注意：JSON 顶层不能有外层包装。")
        return 1

    print("OK 可被青柠简历正常导入")
    if stats and not quiet:
        print(f"   栏目 {stats['sections']} 个（显示 {stats['visible']}，自定义 {stats['custom']}）"
              f" / 条目 {stats['entries']} 条 / 正文约 {stats['chars']} 字")
    if warnings and not quiet:
        print(f"\n提示 {len(warnings)} 条（不影响导入）：")
        for w in warnings:
            print(f"  ! {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

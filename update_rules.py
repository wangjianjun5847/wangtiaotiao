#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""李跳跳（LiTiaotiao）自用去广告规则 · 更新脚本

功能：
    拉取社区规则源 → 按 App 包名的 Java hashCode 匹配 → 去重合并 →
    重新生成李跳跳可直接导入的 MyRules.json，并输出与旧版的变更报告。

收录范围（SCOPE）：
    "all"    = 4 个规则源里的全部应用，一个不漏（当前设置）
    "target" = 只收录下方 APPS 清单内的应用（改这一行即可切换）

用法：
    python update_rules.py

依赖：
    - git（拉取规则源；SSL 校验失败时会自动关闭校验重试，兼容企业代理）
    - Python 3.8+

说明：
    - 坐标点击类规则（action 形如 x:289y:191）依赖设备分辨率，统一跳过并计数
    - 只收录有 popup_rules 的条目；纯服务开关（ltt_service）等无规则条目不导入
    - ltt_service 是个人设备设置（false 会误关服务），导入时统一去除
    - 规则键为 App 包名的 String.hashCode()，与李跳跳官方格式一致
"""
import json
import os
import re
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "sources")
OUT_PATH = os.path.join(BASE_DIR, "MyRules.json")

SCOPE = "all"   # "all" = 全量收录；"target" = 仅 APPS 清单

# ---------- 规则源（按新鲜度排序，越靠前越优先作为合并基础） ----------
SOURCES = [
    {
        "name": "743859910",
        "url": "https://github.com/743859910/LiTiaoTiao_Custom_Rules.git",
        "file": "LiTiaotiao_Custom_Rules.txt",
        "label": "社区精选版",
        "kind": "hash",
        "branch": None,
    },
    {
        "name": "henry",
        "url": "https://github.com/Henry-bai3006/litiaotiao_rules.git",
        "file": "rules/879.txt",
        "label": "网络合集",
        "kind": "hash",
        "branch": None,
    },
    {
        "name": "rongzhiy",
        "url": "https://github.com/rongzhiy/LiTiaotiao.git",
        "file": "AllRules.json",
        "label": "上游仓库自带版",
        "kind": "hash",
        "branch": None,
    },
    {
        "name": "supp-3316134332",
        "url": "https://github.com/3316134332/litiaotiao-rule.git",
        "file": "rules.json",
        "label": "补充规则",
        "kind": "supp",
        "branch": None,
    },
    {
        "name": "applist",
        "url": "https://github.com/wtwang1998/LiTiaotiao-Custom-Rules.git",
        "file": "AppList.md",
        "label": "官方应用名录",
        "kind": "applist",
        "branch": "main",
    },
]

# ---------- SCOPE="target" 时的目标清单（保留作参考与快速切换） ----------
APPS = [
    ("com.tencent.mm", "微信"),
    ("com.tencent.mobileqq", "QQ"),
    ("com.taobao.taobao", "淘宝"),
    ("com.jingdong.app.mall", "京东"),
    ("com.xunmeng.pinduoduo", "拼多多"),
    ("com.ss.android.ugc.aweme", "抖音"),
    ("com.smile.gifmaker", "快手"),
    ("com.xingin.xhs", "小红书"),
    ("tv.danmaku.bili", "哔哩哔哩"),
    ("com.zhihu.android", "知乎"),
    ("com.sina.weibo", "微博"),
    ("com.netease.cloudmusic", "网易云音乐"),
    ("com.tencent.qqmusic", "QQ音乐"),
    ("com.autonavi.minimap", "高德地图"),
    ("com.baidu.searchbox", "百度"),
    ("com.baidu.netdisk", "百度网盘"),
    ("com.tencent.qqlive", "腾讯视频"),
    ("com.qiyi.video", "爱奇艺"),
    ("com.youku.phone", "优酷"),
    ("com.hunantv.imgo.activity", "芒果TV"),
    ("com.kugou.android", "酷狗音乐"),
    ("com.ximalaya.ting.android", "喜马拉雅"),
    ("com.dragon.read", "番茄免费小说"),
    ("com.sankuai.meituan", "美团"),
    ("me.ele", "饿了么"),
    ("com.sdu.didi.psnger", "滴滴出行"),
    ("com.baidu.BaiduMap", "百度地图"),
    ("com.cainiao.wireless", "菜鸟裹裹"),
    ("com.shizhuang.duapp", "得物"),
    ("com.lianjia.beike", "贝壳找房"),
    ("com.ss.android.article.news", "今日头条"),
    ("com.netease.news", "网易新闻"),
    ("com.tencent.news", "腾讯新闻"),
    ("com.dongqiudi.news", "懂球帝"),
    ("com.hupu.games", "虎扑"),
    ("com.baidu.tieba", "百度贴吧"),
    ("com.cubic.autohome", "汽车之家"),
]

# ---------- 补充规则源的 appName → 包名（均已逐一核实） ----------
SUPP_PKG = {
    "微信": "com.tencent.mm",
    "抖音": "com.ss.android.ugc.aweme",
    "阿里云盘": "com.alicloud.databox",
    "汽水音乐": "com.luna.music",
    "中国移动云盘": "com.chinamobile.mcloud",
    "123云盘": "com.mfcloudcalculate.networkdisk",
    "i音乐(iqoo/vivo音乐)": "com.android.bbkmusic",
}

# 哈希算法自检：已知应用 → 已知哈希（来自官方规则库样本）
SELF_TESTS = [
    ("com.coolapk.market", 847156324),   # 酷安
    ("com.dragon.read", 949069732),      # 番茄免费小说
]


def lenient_loads(s):
    """宽松 JSON 解析：容忍尾随逗号（社区规则文件常见，App 的 Gson 解析器同样容忍）"""
    return json.loads(re.sub(r",\s*([}\]])", r"\1", s))


def java_hash(s):
    """Java String.hashCode() 的 Python 实现（32 位有符号回绕）"""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    if h >= 2 ** 31:
        h -= 2 ** 32
    return h


def run_git(args, cwd=None):
    return subprocess.run(
        ["git"] + args, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )


def fetch(src):
    """克隆或更新一个规则源仓库，返回本地目录；失败返回 None"""
    dest = os.path.join(SRC_DIR, src["name"])
    target = os.path.join(dest, src["file"])
    if os.path.isdir(os.path.join(dest, ".git")):
        for extra in ([], ["-c", "http.sslVerify=false"]):
            r = run_git(extra + ["pull", "--ff-only", "--quiet"], cwd=dest)
            if r.returncode == 0:
                return dest if os.path.exists(target) else None
        print(f"  [warn] {src['name']} 更新失败，使用本地已有副本")
        return dest if os.path.exists(target) else None
    for extra in ([], ["-c", "http.sslVerify=false"]):
        args = extra + ["clone", "--depth", "1", "--quiet"]
        if src.get("branch"):
            args += ["--branch", src["branch"]]
        args += [src["url"], dest]
        r = run_git(args)
        if r.returncode == 0 and os.path.exists(target):
            return dest
    tail = (r.stdout or "").strip().splitlines()
    print(f"  [warn] {src['name']} 克隆失败：{tail[-1] if tail else src['url']}")
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    return None


def load_hash_map(path):
    """加载 [{hash: jsonstr}, ...] 格式，返回 ({int_hash: dict}, 解析失败数)"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out, bad = {}, 0
    for entry in data:
        for k, v in entry.items():
            try:
                key = int(k)
            except ValueError:
                continue  # 跳过全局配置项（foreground_service 等个人设置）
            try:
                out[key] = lenient_loads(v) if isinstance(v, str) else v
            except Exception:
                bad += 1  # 解析失败的条目无法使用，跳过
    return out, bad


def load_supp(path):
    """加载 3316134332 的 [{appName, rule}, ...] 格式"""
    supp = {}
    with open(path, encoding="utf-8") as f:
        for item in json.load(f):
            try:
                supp[item["appName"]] = json.loads(item["rule"])
            except Exception:
                continue
    return supp


def load_applist(path):
    """解析官方 AppList.md，返回 {hash: 中文名}"""
    names = {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for m in re.finditer(r"\[([A-Za-z0-9._]+)\]\([^)]*\)(?:（([^）]+)）)?", text):
        pkg, name = m.group(1), m.group(2)
        if pkg and name:
            names[java_hash(pkg)] = name
    return names


def rule_keys(obj):
    return {(r.get("id"), str(r.get("action", ""))) for r in obj.get("popup_rules", [])}


def main():
    # ---------- 1/5 拉取规则源 ----------
    print("== 1/5 拉取规则源 ==")
    os.makedirs(SRC_DIR, exist_ok=True)
    loaded, supp, name_map = [], {}, {}
    bad_total = 0
    for src in SOURCES:
        dest = fetch(src)
        if not dest:
            continue
        fpath = os.path.join(dest, src["file"])
        if not os.path.exists(fpath):
            print(f"  [warn] {src['name']} 中未找到 {src['file']}，跳过")
            continue
        if src["kind"] == "hash":
            m, bad = load_hash_map(fpath)
            bad_total += bad
            loaded.append((src["label"], m))
            print(f"  [ok] {src['label']:<14} {len(m)} 个应用")
        elif src["kind"] == "supp":
            supp = load_supp(fpath)
            print(f"  [ok] {src['label']:<14} {len(supp)} 个应用")
        elif src["kind"] == "applist":
            name_map = load_applist(fpath)
            print(f"  [ok] {src['label']:<14} {len(name_map)} 个应用可命名")

    if not loaded:
        print("\n错误：没有可用的规则源（请检查网络后重试）。")
        sys.exit(1)

    # 本地已知名称优先补充进名录
    for pkg, name in APPS:
        name_map.setdefault(java_hash(pkg), name)
    for name, pkg in SUPP_PKG.items():
        name_map.setdefault(java_hash(pkg), name)

    def appname(h):
        return name_map.get(h, f"hash={h}")

    # ---------- 2/5 哈希自检 + 确定收录范围 ----------
    print("\n== 2/5 哈希自检与收录范围 ==")
    for pkg, expect in SELF_TESTS:
        h = java_hash(pkg)
        print(f"  [{'PASS' if h == expect else 'FAIL'}] {pkg} -> {h}")

    if SCOPE == "all":
        hashes, seen = [], set()
        for label, m in loaded:
            for h in m:
                if h not in seen:
                    seen.add(h)
                    hashes.append(h)
        # 补充源独有的 App（不在任何哈希源里）也要建条目，一个不漏
        for app_name, pkg in SUPP_PKG.items():
            h = java_hash(pkg)
            if h not in seen:
                seen.add(h)
                hashes.append(h)
        print(f"  全量模式：4 个源合并后共 {len(hashes)} 个应用")
    else:
        hashes, missing = [], []
        for pkg, name in APPS:
            h = java_hash(pkg)
            if any(h in m for _, m in loaded):
                hashes.append(h)
            else:
                missing.append(name)
        print(f"  目标模式：覆盖 {len(hashes)}/{len(APPS)} 个 App"
              f"{'；未收录: ' + '、'.join(missing) if missing else ''}")

    # ---------- 3/5 合并 ----------
    print("\n== 3/5 合并规则 ==")
    merged = {}
    coord_skipped = 0
    dropped = 0
    for h in hashes:
        base, base_idx = None, None
        for i, (label, m) in enumerate(loaded):
            if h in m:
                base, base_idx = m[h], i
                break
        obj = json.loads(json.dumps(base)) if base is not None else {}
        rules, seen_keys = [], set()

        def add(raw_rules):
            nonlocal coord_skipped
            for r in raw_rules:
                act = str(r.get("action", ""))
                if act.startswith("x:"):
                    coord_skipped += 1  # 坐标点击依赖设备分辨率，跳过
                    continue
                key = (r.get("id"), act)
                if key not in seen_keys:
                    seen_keys.add(key)
                    rules.append(r)

        add(obj.get("popup_rules", []))
        for i, (label, m) in enumerate(loaded):
            if i == base_idx or h not in m:
                continue
            add(m[h].get("popup_rules", []))
        for app_name, pkg in SUPP_PKG.items():
            if java_hash(pkg) == h and app_name in supp:
                add(supp[app_name].get("popup_rules", []))

        obj.pop("ltt_service", None)  # 个人设备开关，false 会误关服务，统一去除
        has_other_rules = any(k in obj for k in ("click_way_popup", "unite_popup_rules"))
        if not rules and not has_other_rules:
            dropped += 1  # 纯服务开关等无规则条目，导入只会添空壳
            continue
        obj["popup_rules"] = rules
        merged[h] = obj

    # ---------- 4/5 对比旧版 ----------
    print("\n== 4/5 变更报告 ==")
    old = {}
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as f:
                for e in json.load(f):
                    for k, v in e.items():
                        try:
                            old[int(k)] = lenient_loads(v)
                        except Exception:
                            pass
        except Exception:
            old = {}

    old_total = sum(len(v.get("popup_rules", [])) for v in old.values())
    new_total = sum(len(v.get("popup_rules", [])) for v in merged.values())
    added_apps = [h for h in merged if h not in old]
    removed_apps = [h for h in old if h not in merged]
    changed = []
    for h in merged:
        if h in old and rule_keys(merged[h]) != rule_keys(old[h]):
            changed.append(h)

    if added_apps:
        print(f"  [新增 App] 共 {len(added_apps)} 个：")
        line = "      "
        for h in added_apps:
            piece = appname(h) + "、"
            if len(line) + len(piece) > 100:
                print(line.rstrip("、"))
                line = "      "
            line += piece
        if line.strip():
            print(line.rstrip("、"))
    for h in changed:
        a = rule_keys(merged[h]) - rule_keys(old[h])
        r = rule_keys(old[h]) - rule_keys(merged[h])
        print(f"  [规则变化] {appname(h)}: +{len(a)} / -{len(r)}")
        for rid, act in sorted(a, key=lambda x: (str(x[0]), x[1]))[:5]:
            print(f"      + {rid} -> {act}")
        for rid, act in sorted(r, key=lambda x: (str(x[0]), x[1]))[:5]:
            print(f"      - {rid} -> {act}")
    if removed_apps:
        print(f"  [移除 App] 共 {len(removed_apps)} 个: "
              + "、".join(appname(h) for h in removed_apps[:20]))
    if not added_apps and not changed and not removed_apps:
        print("  与旧版完全一致，无变化。")
    print(f"  合计：{len(merged)} 个 App / {new_total} 条规则"
          f"（旧版 {len(old)} 个 App / {old_total} 条）")
    print(f"  跳过坐标点击类规则 {coord_skipped} 条；跳过无法解析的条目 {bad_total} 条")
    print(f"  跳过无规则条目 {dropped} 个（纯服务开关等，无广告规则可导）")
    named = sum(1 for h in merged if h in name_map)
    print(f"  其中 {named} 个 App 可在官方名录中查到中文名")

    # ---------- 5/5 写出 ----------
    out_entries = [{str(h): json.dumps(merged[h], ensure_ascii=False)} for h in merged]
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_entries, f, ensure_ascii=False, indent="\t")
    print(f"\n已生成 {OUT_PATH}（{len(merged)} 个 App，{os.path.getsize(OUT_PATH)} 字节）")
    print("下一步：把 MyRules.json 导入李跳跳"
          "（更多 → 右上角三点 → 导入规则 → 长按粘贴 → 保存）")


if __name__ == "__main__":
    main()

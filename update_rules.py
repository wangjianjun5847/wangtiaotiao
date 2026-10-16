#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""李跳跳（LiTiaotiao）自用去广告规则 · 更新脚本

用途：
    拉取 4 个社区规则源的最新规则，按 App 包名的 Java hashCode 匹配、去重合并，
    重新生成李跳跳可直接导入的 MyRules.json，并输出与旧版的变更报告。

用法：
    python update_rules.py

依赖：
    - git（拉取规则源；SSL 校验失败时会自动关闭校验重试，兼容企业代理）
    - Python 3.8+

更新后：
    把新生成的 MyRules.json 导入李跳跳即完成更新（导入为覆盖式，直接导新文件即可，
    不需要先删除旧规则）。
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

# ---------- 规则源（按新鲜度排序，越靠前越优先作为合并基础） ----------
SOURCES = [
    {
        "name": "743859910",
        "url": "https://github.com/743859910/LiTiaoTiao_Custom_Rules.git",
        "file": "LiTiaotiao_Custom_Rules.txt",
        "label": "社区精选版",
        "kind": "hash",
    },
    {
        "name": "henry",
        "url": "https://github.com/Henry-bai3006/litiaotiao_rules.git",
        "file": "rules/879.txt",
        "label": "网络合集",
        "kind": "hash",
    },
    {
        "name": "rongzhiy",
        "url": "https://github.com/rongzhiy/LiTiaotiao.git",
        "file": "AllRules.json",
        "label": "上游仓库自带版",
        "kind": "hash",
    },
    {
        "name": "3316134332",
        "url": "https://github.com/3316134332/litiaotiao-rule.git",
        "file": "rules.json",
        "label": "微信/抖音补充规则",
        "kind": "supp",
    },
]

# ---------- 目标 App 清单（包名 → 名称） ----------
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

# 3316134332 的补充规则中，只采纳这些 App（按 appName 匹配）
SUPP_PKG = {
    "抖音": "com.ss.android.ugc.aweme",
    "微信": "com.tencent.mm",
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
        r = run_git(extra + ["clone", "--depth", "1", "--quiet", src["url"], dest])
        if r.returncode == 0 and os.path.exists(target):
            return dest
    tail = (r.stdout or "").strip().splitlines()
    print(f"  [warn] {src['name']} 克隆失败：{tail[-1] if tail else src['url']}")
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    return None


def load_hash_map(path):
    """加载 [{hash: jsonstr}, ...] 格式，返回 {int_hash: dict}"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for entry in data:
        for k, v in entry.items():
            try:
                key = int(k)
            except ValueError:
                continue  # 跳过全局配置项（foreground_service 等个人设置）
            try:
                out[key] = lenient_loads(v) if isinstance(v, str) else v
            except Exception:
                out[key] = {"_raw": v}
    return out


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


def rule_keys(obj):
    return {(r.get("id"), r.get("action")) for r in obj.get("popup_rules", [])}


def main():
    # ---------- 1/4 拉取规则源 ----------
    print("== 1/4 拉取规则源 ==")
    os.makedirs(SRC_DIR, exist_ok=True)
    loaded, supp = [], {}
    for src in SOURCES:
        dest = fetch(src)
        if not dest:
            continue
        fpath = os.path.join(dest, src["file"])
        if not os.path.exists(fpath):
            print(f"  [warn] {src['name']} 中未找到 {src['file']}，跳过")
            continue
        if src["kind"] == "hash":
            m = load_hash_map(fpath)
            loaded.append((src["label"], m))
            print(f"  [ok] {src['label']:<14} {len(m)} 个应用")
        else:
            supp = load_supp(fpath)
            print(f"  [ok] {src['label']:<14} {len(supp)} 个应用")
    if not loaded:
        print("\n错误：没有可用的规则源（请检查网络后重试）。")
        sys.exit(1)

    # ---------- 2/4 哈希自检 + 覆盖检查 ----------
    print("\n== 2/4 哈希自检与覆盖检查 ==")
    for pkg, expect in SELF_TESTS:
        h = java_hash(pkg)
        print(f"  [{'PASS' if h == expect else 'FAIL'}] {pkg} -> {h}")

    covered, missing = [], []
    for pkg, name in APPS:
        h = java_hash(pkg)
        hits = [label for label, m in loaded if h in m]
        (covered if hits else missing).append((pkg, name, h))
    print(f"  覆盖 {len(covered)}/{len(APPS)} 个 App"
          f"{'；未收录: ' + '、'.join(n for _, n, _ in missing) if missing else ''}")

    # ---------- 3/4 合并 ----------
    print("\n== 3/4 合并规则 ==")
    merged = {}
    for pkg, name, h in covered:
        base, base_idx = None, None
        for i, (label, m) in enumerate(loaded):
            if h in m:
                base, base_idx = m[h], i
                break
        obj = json.loads(json.dumps(base))  # deep copy
        rules = obj.setdefault("popup_rules", [])
        seen = rule_keys(obj)

        for i, (label, m) in enumerate(loaded):
            if i == base_idx or h not in m:
                continue
            for r in m[h].get("popup_rules", []):
                key = (r.get("id"), r.get("action"))
                if key not in seen:
                    rules.append(r)
                    seen.add(key)

        # 3316134332 补充（坐标点击类规则依赖设备分辨率，跳过）
        if name in SUPP_PKG and name in supp:
            for r in supp[name].get("popup_rules", []):
                if str(r.get("action", "")).startswith("x:"):
                    continue
                key = (r.get("id"), r.get("action"))
                if key not in seen:
                    rules.append(dict(r))
                    seen.add(key)

        merged[h] = obj

    # ---------- 4/4 对比旧版 + 写出 ----------
    print("\n== 4/4 变更报告 ==")
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
    changes = 0
    for pkg, name, h in covered:
        if h not in old:
            print(f"  [新增 App] {name}（{len(merged[h]['popup_rules'])} 条规则）")
            changes += 1
            continue
        added = rule_keys(merged[h]) - rule_keys(old[h])
        removed = rule_keys(old[h]) - rule_keys(merged[h])
        if added or removed:
            changes += 1
            print(f"  [规则变化] {name}: +{len(added)} / -{len(removed)}")
            for rid, act in sorted(added, key=lambda x: (str(x[0]), str(x[1])))[:5]:
                print(f"      + {rid} -> {act}")
            for rid, act in sorted(removed, key=lambda x: (str(x[0]), str(x[1])))[:5]:
                print(f"      - {rid} -> {act}")
    for h in old:
        if h not in merged:
            print(f"  [移除 App] hash={h}")
            changes += 1
    if changes == 0:
        print("  与旧版完全一致，无变化。")
    print(f"  合计：{len(merged)} 个 App / {new_total} 条规则"
          f"（旧版 {len(old)} 个 App / {old_total} 条）")

    out_entries = [{str(h): json.dumps(merged[h], ensure_ascii=False)} for h in merged]
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_entries, f, ensure_ascii=False, indent="\t")
    print(f"\n已生成 {OUT_PATH}（{os.path.getsize(OUT_PATH)} 字节）")
    print("下一步：把 MyRules.json 导入李跳跳"
          "（更多 → 右上角三点 → 导入规则 → 长按粘贴 → 保存）")


if __name__ == "__main__":
    main()

# 李跳跳自用去广告规则（wangtiaotiao）

基于社区规则库合并生成的自用规则集：**一次导入，覆盖 36 个常用 App 的开屏广告、弹窗广告、更新提醒、权限索取等干扰弹窗，共 152 条规则**。规则格式与李跳跳官方规则完全一致，可直接导入。

李跳跳（LiTiaotiao）是一款 Android 跳过广告类应用（基于无障碍服务），官方已于 2023 年 8 月停更；本仓库规则来自仍在更新的社区规则源，会持续跟进。

## 文件说明

| 文件 | 说明 |
|---|---|
| `MyRules.json` | 规则主文件，**导入李跳跳用的就是这个** |
| `update_rules.py` | 更新脚本：拉取社区最新规则源，重新合并生成 `MyRules.json` |
| `README.md` | 本说明 |

## 导入方法（一次性）

1. 把 `MyRules.json` 传到手机（或在手机浏览器里打开本仓库中的该文件，全选复制）
2. 打开李跳跳 → 更多 → 右上角三个点 → 导入规则
3. 长按输入框，选择系统粘贴，点保存
4. 回到李跳跳主界面，确认目标 App 在列表内且开关已打开

注意事项：

- 一次只能导入一个 JSON 文件，再导入其他文件会覆盖、不会合并——所以只导这一个文件
- 不要经微信、输入法等第三方 App 中转复制，可能被截断导致格式错误
- App 卸载重装后规则仍然生效，不需要重复导入

## 更新规则

规则库是"活"的：社区规则源仍在更新，App 升级后老规则可能个别失效。两种更新方式任选：

**方式 A：让我更新（推荐）**
直接对我说"更新一下李跳跳规则"，我会重新拉取社区规则源、合并、生成新版 `MyRules.json` 并告诉你具体改了什么，你再把新文件导入手机即可。也可以让我设置成定期自动更新（当前已设为每两周一次）。

**方式 B：自己更新**
电脑上安装 Python 3.8+ 和 git 后，在本目录执行：

```bash
python update_rules.py
```

脚本会自动完成：克隆/更新 4 个社区规则源 → 按包名 hashCode 匹配 → 去重合并 → 与旧版对比输出变更报告 → 重新生成 `MyRules.json`。把新文件导入李跳跳即完成更新（覆盖式，不用先删旧的）。

## 覆盖清单（36 个 App，152 条规则）

| App | 包名 | 规则数 |
|---|---|---|
| 微博 | com.sina.weibo | 18 |
| 喜马拉雅 | com.ximalaya.ting.android | 12 |
| 抖音 | com.ss.android.ugc.aweme | 10 |
| 百度网盘 | com.baidu.netdisk | 9 |
| 得物 | com.shizhuang.duapp | 8 |
| 拼多多 | com.xunmeng.pinduoduo | 7 |
| 芒果TV | com.hunantv.imgo.activity | 7 |
| QQ音乐 | com.tencent.qqmusic | 5 |
| 美团 | com.sankuai.meituan | 5 |
| 懂球帝 | com.dongqiudi.news | 5 |
| 微信 | com.tencent.mm | 4 |
| QQ | com.tencent.mobileqq | 4 |
| 滴滴出行 | com.sdu.didi.psnger | 4 |
| 百度地图 | com.baidu.BaiduMap | 4 |
| 腾讯新闻 | com.tencent.news | 4 |
| 淘宝 | com.taobao.taobao | 3 |
| 京东 | com.jingdong.app.mall | 3 |
| 高德地图 | com.autonavi.minimap | 3 |
| 爱奇艺 | com.qiyi.video | 3 |
| 番茄免费小说 | com.dragon.read | 3 |
| 饿了么 | me.ele | 3 |
| 贝壳找房 | com.lianjia.beike | 3 |
| 今日头条 | com.ss.android.article.news | 3 |
| 快手 | com.smile.gifmaker | 2 |
| 小红书 | com.xingin.xhs | 2 |
| 哔哩哔哩 | tv.danmaku.bili | 2 |
| 知乎 | com.zhihu.android | 2 |
| 网易云音乐 | com.netease.cloudmusic | 2 |
| 腾讯视频 | com.tencent.qqlive | 2 |
| 优酷 | com.youku.phone | 2 |
| 菜鸟裹裹 | com.cainiao.wireless | 2 |
| 虎扑 | com.hupu.games | 2 |
| 百度 | com.baidu.searchbox | 1 |
| 酷狗音乐 | com.kugou.android | 1 |
| 百度贴吧 | com.baidu.tieba | 1 |
| 汽车之家 | com.cubic.autohome | 1 |

## 规则来源与合并方式

| 来源 | 更新情况 | 说明 |
|---|---|---|
| 743859910/LiTiaoTiao_Custom_Rules | 2026-10 | 社区精选版，与官方归档库 wtwang1998/LiTiaotiao-Custom-Rules 内容一致 |
| Henry-bai3006/litiaotiao_rules | 2026-10 | 网络合集，874 条规则 |
| rongzhiy/LiTiaotiao | 2024-05 | 上游仓库自带版本 |
| 3316134332/litiaotiao-rule | 2026-10 | 微信、抖音的补充规则 |

合并方式：以最新源为基础对象，其余源按 id + action 去重后追加；坐标点击类规则（如 `x:289y:191`）依赖设备分辨率，未纳入。

## 未收录 App

网易新闻（com.netease.news）：上述规则源均未收录。可在李跳跳内自行录制自定义规则，或换用 GKD（github.com/gkd-kit/gkd，社区推荐的继任项目）。

## 已知边界

- 李跳跳官方已停更，规则对最新版 App 可能有个别失效。遇到漏网弹窗：李跳跳 → 更多 → 设置 → 选中该 App，手动补规则
- 百度、酷狗音乐、百度贴吧、汽车之家、哔哩哔哩目前各仅 1~2 条社区规则，属收录现状，不是漏收

最近更新：2026-10-16

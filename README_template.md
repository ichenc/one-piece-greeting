<div align="center">

<img src="assets/wanted.svg?v={{DATE_COMPACT}}" width="360" alt="今日通缉令 · {{CHAR_ZH}}">

# 🏴‍☠️ 今日的悬赏目标：**{{CHAR_ZH}}**

<sub>{{CHAR_EN}} · {{EPITHET}} · No. {{SERIAL}} / {{TOTAL}}</sub>

### 「{{LINE}}」

**{{GREETING}}**

<sub>ONE PIECE · 每日通缉令 · {{DATE_LABEL}}（{{WEEKDAY}}）</sub>

</div>

---

## 📋 悬赏档案

| 项目 | 内容 |
| :--- | :--- |
| 🪙 悬赏金 | **{{BOUNTY_NUM}}**（{{BOUNTY_DESC}}） |
| 🏴‍☠️ 所属 | {{CREW}} · {{ROLE}} |
| 🍈 恶魔果实 | {{FRUIT}} |
| ✨ 霸气 | {{HAKI}} |
| 🎂 生日 | {{BIRTHDAY}} |
| 📏 身高 | {{HEIGHT}} |
| 🗺️ 初次登场 | {{DEBUT}} |
| 🏷️ 标签 | {{TAG}} |

## ⚔️ 能力评估

| 能力 | 数值 | 条 |
| :--- | :---: | :--- |
{{STAT_ROWS}}

## 💬 今日一句

> {{LINE}}

## 🗓️ 最近登场

| 日期 | 角色 | 悬赏金 |
| :--- | :--- | :--- |
{{HISTORY_ROWS}}

---

<div align="center">

🌟 **这个 README 每天自动换一位《海贼王》角色** 🌟<br>
每天 UTC 00:00（北京时间 08:00）由 GitHub Actions 重新生成并提交 · 共收录 {{TOTAL}} 位角色<br>
<sub>生成日期：{{DATE_ISO}}（北京时间）· 也可以在 Actions 页手动点一次「Run workflow」</sub>

</div>

<details>
<summary>🛠️ 它是怎么工作的？</summary>

<br>

| 文件 | 作用 |
| :--- | :--- |
| `.github/workflows/daily.yml` | 定时 + 手动触发，跑完自动提交 |
| `generate.py` | 按日期确定性选角、绘制通缉令、生成 README（纯标准库） |
| `characters.json` | 角色资料库，想加角色直接往里补一条 |
| `assets/wanted.svg` | 当天重绘的通缉令，角色图内嵌在 SVG 里，不依赖任何外链 |
| `assets/characters/` | 48 位角色的立绘，统一裁成 420×240 透明 PNG |
| `history.json` | 登场记录，避免短期内抽到同一个角色 |
| `README_template.md` | 本页的模板，`{{占位符}}` 每天被替换 |
| `tools/prepare_portraits.py` | 可选工具：重新下载并裁切角色立绘（需要 Pillow，主流程不依赖） |

选角规则：以当天日期做哈希，从「最近 15 天没登场过」的角色里挑一位。所以**同一天永远得到同一张通缉令**，不会重复提交；不同日期则会换人。

```bash
python generate.py                        # 本地生成今天
python generate.py --date 2026-12-25      # 看看圣诞节会抽到谁
python generate.py --character zoro       # 指定角色
```

</details>

<sub>📜 {{DATA_NOTE}} 角色立绘取自 One Piece Wiki / Vivre Card 粉丝资料库，仅作裁切缩放并内嵌于自绘 SVG；《ONE PIECE》相关版权归尾田荣一郎 / 集英社等所有，本项目为非商业的粉丝展示。</sub>

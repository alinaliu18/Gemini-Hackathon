# Interview Maestro 设计系统 v1

配套演示：`design-demo.html`（4 个页面：首页 / 准备 / 面试中 / 报告）。

## 方向

一句话：**像一份可以核对的体检报告，而不是一个在给你打分的舞台。**

- 现状问题不在颜色：hero 占满一屏、渐变和光晕、所有选项一次铺开、emoji 当图标、Playfair 衬线标题。这些让它像作品集，不像工具。
- 成熟感靠三件事：少（每屏一个主操作）、准（数字带单位、可点回原话）、稳（中性色占 90% 面积，强调色只给"下一步"和"可点的证据"）。
- 低压力：面试中不显示任何分数和实时评价；报告先给"3 件要改的事"，总分降为一行小字。

## 1. 颜色

中性色带一点青绿偏色（和强调色同一色相），不是纯灰。强调色只有一个：墨青。语义色（成功/警告/危险）只用于状态，不算强调色。

| 用途 | CSS 变量 | 浅色 | 深色 |
|---|---|---|---|
| 页面底色 | `--color-bg` | `#F4F6F5` | `#101516` |
| 卡片/窗口表面 | `--color-surface` | `#FFFFFF` | `#171F20` |
| 下沉区（输入框、引用、面试舞台） | `--color-surface-sunken` | `#EDF1F0` | `#1D2729` |
| 分隔线、默认边框 | `--color-border` | `#DCE2E0` | `#2A3537` |
| 强边框（hover、输入框） | `--color-border-strong` | `#BFC9C6` | `#3B4A4C` |
| 正文 | `--color-text` | `#172123` | `#E4EBEA` |
| 次要文字 | `--color-text-secondary` | `#4A5759` | `#A7B4B4` |
| 辅助文字（时间、注释） | `--color-text-tertiary` | `#667375` | `#7F8D8E` |
| 强调色（主按钮、链接、选中） | `--color-accent` | `#1D6470` | `#62B5C0` |
| 强调色 hover | `--color-accent-hover` | `#154E58` | `#82C6CF` |
| 强调色浅底（选中卡片、时间戳 chip） | `--color-accent-subtle` | `#E2EEEF` | `#163338` |
| 强调色上的文字 | `--color-on-accent` | `#FFFFFF` | `#0A1A1C` |
| 成功 | `--color-success` / `--color-success-subtle` | `#2C7A4E` / `#E3F1E8` | `#63C38F` / `#14301F` |
| 警告 | `--color-warning` / `--color-warning-subtle` | `#8F5B00` / `#F7EDD9` | `#E2AC4E` / `#33280F` |
| 危险 | `--color-danger` / `--color-danger-subtle` | `#AE3A30` / `#F7E5E2` | `#EE7F74` / `#3A1C19` |
| 摄像头画面占位 | `--color-tile` | `#26302F` | `#0B1011` |
| 阴影色 | `--shadow-color` | `rgb(16 30 32 / 0.08)` | `rgb(0 0 0 / 0.4)` |

用法规则：
- 强调色每屏只出现在主按钮、选中态、时间戳 chip、焦点环上。不要用它画装饰。
- "待改进"用 warning，不用 danger。danger 只给"结束面试"和真正的错误（麦克风没声音）。
- 三个赛道不再各配一个颜色（现在的 `--academic/--career/--social` 删掉）。赛道靠文字和图标区分。

## 2. 字体

Google Fonts，两款：

| 变量 | 值 | 用途 |
|---|---|---|
| `--font-sans` | `"Instrument Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif` | 所有界面文字和标题 |
| `--font-mono` | `"IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace` | 时间戳、计时器、指标数字、单位 |

引入：`https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap`

字号（px / 行高）：

| 变量 | 字号/行高 | 用途 |
|---|---|---|
| `--fs-caption` | 12 / 16 | 注释、窗口路径、表单提示 |
| `--fs-label` | 13 / 18 | 标签、chip、小标题（大写时字距 0.06em） |
| `--fs-body-sm` | 14 / 20 | 界面正文、按钮 |
| `--fs-body` | 16 / 24 | 报告正文、问题描述 |
| `--fs-lead` | 18 / 28 | 首页副标题 |
| `--fs-h3` | 22 / 28 | 页面标题、面试中的当前问题 |
| `--fs-h2` | 28 / 34 | 报告标题 |
| `--fs-h1` | 36 / 42 | 只用于首页那一句承诺（手机上降到 28） |

字重只用 400 / 500 / 600。不用斜体、不用全大写标题。标题加 `text-wrap: balance`。

## 3. 间距、圆角、阴影

间距（4 的倍数）：`--space-1` 4 · `--space-2` 8 · `--space-3` 12 · `--space-4` 16 · `--space-5` 24 · `--space-6` 32 · `--space-7` 48 · `--space-8` 64。手机两侧留白固定 16（`--space-4`）。

圆角：`--radius-sm` 4（chip）· `--radius-md` 8（按钮、输入框、引用块）· `--radius-lg` 12（卡片、窗口、视频画面）· `--radius-full` 999（圆形通话按钮、状态胶囊）。

阴影（克制使用）：
- `--shadow-1`：`0 1px 2px var(--shadow-color)`，只给悬浮在画面上的自己摄像头小窗。
- `--shadow-2`：`0 8px 24px var(--shadow-color)`，只给弹出菜单和对话框。
- 卡片一律用 1px `--color-border` 分隔，不加阴影。

动效：`--dur-fast` 120ms（hover、按下）· `--dur` 200ms（展开、切换）。面试官状态的呼吸/音波动画在 `prefers-reduced-motion` 下关闭，只保留文字状态。

## 4. 组件

**按钮**（高 40，手机上主按钮可拉满宽度；字号 `--fs-body-sm`，字重 500，圆角 `--radius-md`）
- Primary：底 `--color-accent`，字 `--color-on-accent`，hover 换 `--color-accent-hover`。每屏最多一个。
- Secondary：底 `--color-surface`，1px `--color-border-strong`，字 `--color-text`。
- Ghost：无底无边，字 `--color-accent`；用于"Skip""Practice one question"这类次要入口。
- 所有按钮焦点：`outline: 2px solid var(--color-accent); outline-offset: 2px`。

**赛道卡片 Track card**：本质是单选框（`<input type="radio">` + `<label>`）。底 `--color-surface`，1px `--color-border`，圆角 `--radius-lg`，内边距 `--space-4`。内容：图标（20px 线性）+ 名称（`--fs-body` 600）+ 一行说明（`--fs-body-sm` 次要色）。选中：边框 `--color-accent` 2px（用 inset box-shadow 实现，避免跳动）+ 底 `--color-accent-subtle` + 右上角勾。三张等宽，手机上纵向堆叠。

**Chip（状态）**：高 22，内边距 0 8，圆角 `--radius-sm`，字号 `--fs-label` 500。四种：中性（`--color-surface-sunken` / 次要色）、成功、警告、"Not measured"（中性底 + 虚线边框，表示"没测到"不是"差"）。

**时间戳 Chip**：可点击，`--font-mono`，`tabular-nums`，底 `--color-accent-subtle`，字 `--color-accent`，左侧 10px 播放三角。区间写成 `3:02–3:40`。点击后报告顶部的录音播放条跳到该时刻。

**电平表 Meter**：20 格横条，每格 4×16，间距 2。亮格用 `--color-success`，最后 3 格（过载）用 `--color-warning`，未亮格 `--color-border`。旁边文字状态："Mic is working" / "We can't hear you. Check the mic in your system settings."（danger）。
报告里的"区间表"是同一家族：一根灰轨道 + 目标区间（`--color-accent-subtle`）+ 你的值（`--color-text` 竖线），两端标刻度。

**通话控制栏**：只有两个按钮，居中。Mute：48px 圆形 secondary 按钮，`aria-pressed`；静音后图标换成划线麦克风，底变 `--color-warning-subtle`。End：胶囊按钮，底 `--color-danger-subtle`，字 `--color-danger`，文字 "End interview"。没有设置、聊天、字幕开关。

**面试官状态**：圆形头像（抽象标志，不用人脸）+ 状态胶囊。Listening = 外圈缓慢呼吸；Speaking = 5 根音波条；Thinking = 3 个点依次变亮。文字永远在，动画只是辅助。

**报告条目 Report item**：一条 = 标题（一句可执行的话）+ 证据（时间戳 chip + 原话引用或测量值）+ "Try" 改法。默认折叠只显示标题和 chip，点开看引用和改法（`<details>`，第一条默认展开）。引用块：`--color-surface-sunken` 底，`--radius-md`，正文色，不加左侧色条。指标行：左列名称 + 测量值（mono，带单位），右列状态 chip，下面一行解释。

## 5. 规则

1. 每屏只有一个 Primary 按钮。其他操作用 Secondary 或 Ghost。
2. 不用 emoji，图标统一为 1.5px 线性 SVG。
3. 不用渐变（背景、文字、按钮都不用）。不用光晕和装饰性模糊。
4. 不用"卡片墙 + 阴影"。分组靠间距和 1px 分隔线，阴影只给浮层。
5. 所有指标数字用 `--font-mono` + `font-variant-numeric: tabular-nums`，并且带单位：`168 wpm`、`4.3 s`、`74%`、`24 dB`。
6. 每条反馈必须有证据：时间戳 + 原话，或时间戳 + 测量值。没有证据的不显示。
7. 测不到就写 "Not measured" 并说明原因，不打低分、不显示 0。
8. 面试中不显示分数、不实时评价。报告里总分只占一行，排在"3 件要改的事"后面。
9. 不推断情绪：文案里不出现 nervous、confident、anxious。
10. 文案用平实英语，按钮写动作（"Start mock interview"，不写 "Let's go!"），不用破折号。
11. 首页不做满屏 hero，内容高度自适应。

## 6. 落地到代码

- `src/index.css` 的 `:root` 换成本文变量（演示文件顶部 `<style>` 里的三段 `:root` 可以直接复制：浅色、`prefers-color-scheme: dark`、`[data-theme="dark"]`）。
- `src/App.css` 删除 `--monet-*`、Playfair、`.hero-bg-orbs`、所有 `linear-gradient`，组件颜色全部改走变量。
- 原来分 4 步的"选级别 / 加资料 / 选模式"合并成一屏 Setup；"级别"和"补充说明"放进 More options。

# Interview Maestro 设计系统 v2（白 + 蓝）

配套演示：`design-demo.html`（4 个页面：首页 / 准备 / 面试中 / 报告）。只做浅色，不做深色模式。

## 方向

纯白底，一个饱和的钴蓝做品牌色，在少数几处大面积用足；正文用接近黑的墨色。

**招牌元素：对话本身就是主角。**
- 首页：右侧放一段实时转写，面试官的追问用整块蓝色气泡加小音波标出来。直接用产品证明"它会追问"，不写形容词。
- 面试中：整个舞台是一块蓝色面板，问题用大号白字，像在通话；自己的摄像头小窗放在角落。
- 报告：顶部一条横向的会话时间轴是整页的骨架，蓝色编号标记对应"3 件要改的事"，点哪里播放头就跳到哪里。

蓝色只用在这几处大面积位置和主按钮上，其余地方保持白和墨色。

## 1. 颜色

| 用途 | CSS 变量 | 值 |
|---|---|---|
| 页面底色 | `--color-bg` | `#FFFFFF` |
| 卡片/输入框表面 | `--color-surface` | `#FFFFFF` |
| 浅蓝底（转写面板、时间轴、引用块、拖放区） | `--color-tint` | `#F0F4FF` |
| 浅蓝底加深（时间轴的问题分段、hover） | `--color-tint-strong` | `#DDE6FF` |
| 分隔线、默认边框 | `--color-border` | `#E2E7F1` |
| 强边框（输入框、次按钮） | `--color-border-strong` | `#C3CDE2` |
| 正文墨色 | `--color-ink` | `#0A0E1A` |
| 次要文字 | `--color-text-secondary` | `#475069` |
| 辅助文字 | `--color-text-tertiary` | `#69728A` |
| 品牌蓝（主按钮、选中卡片、面试舞台、时间轴标记） | `--color-blue` | `#1D4CF5` |
| 品牌蓝 hover | `--color-blue-hover` | `#1238D8` |
| 深蓝（面试舞台底部的色调过渡、控制栏） | `--color-blue-deep` | `#1332B8` |
| 浅蓝底上的蓝字/链接 | `--color-blue-text` | `#1A40D6` |
| 蓝底上的文字 | `--color-on-blue` | `#FFFFFF` |
| 蓝底上的次要文字 | `--color-on-blue-muted` | `#C4D1FF` |
| 蓝底上的半透明层（状态胶囊、静音按钮边框） | `--color-on-blue-veil` | `rgb(255 255 255 / 0.14)` |
| 成功 | `--color-success` / `--color-success-subtle` | `#0E7A55` / `#E2F5EC` |
| 警告（"待改进"） | `--color-warning` / `--color-warning-subtle` | `#9A5600` / `#FFF0D9` |
| 危险（只给结束面试和真正的错误） | `--color-danger` / `--color-danger-subtle` | `#CC2F25` / `#FDE7E5` |
| 摄像头画面占位 | `--color-tile` / `--color-tile-fg` | `#0F1424` / `#39425A` |
| 阴影色 | `--shadow-color` | `rgb(10 20 60 / 0.12)` |

用法：
- 白底蓝字、蓝底白字的对比度都约 6:1（按 WCAG 公式算），正文可直接用。
- 蓝色"用足"的位置只有：主按钮、选中的赛道卡片（整卡填蓝）、首页追问气泡、面试舞台、报告时间轴标记和编号。不要再拿蓝色画细边框或装饰图标。
- 三个赛道不再各配一色（删掉 `--academic/--career/--social`）。

## 2. 字体

| 变量 | 值 | 用途 |
|---|---|---|
| `--font-display` | `"Bricolage Grotesque", ui-sans-serif, system-ui, sans-serif` | 大标题、面试中的问题、编号数字 |
| `--font-sans` | `"Geist", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif` | 所有界面文字 |
| `--font-mono` | `"Geist Mono", ui-monospace, "SF Mono", Menlo, monospace` | 时间戳、计时器、指标数字和单位 |

引入（三款已请求 Google Fonts 接口确认可用）：
`https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap`

字号（标题大而紧：display 字重 700，字距 -0.03em）：

| 变量 | 值 | 用途 |
|---|---|---|
| `--fs-display-xl` | `clamp(40px, 6.2vw, 68px)`，行高 1.0 | 首页那句承诺 |
| `--fs-display-l` | `clamp(28px, 4.2vw, 42px)`，行高 1.08 | 报告标题、面试中的问题 |
| `--fs-display-m` | `clamp(24px, 3vw, 30px)`，行高 1.1 | 页面标题、报告分节标题 |
| `--fs-lead` | 18px / 28px | 首页副标题、追问气泡 |
| `--fs-body` | 16px / 24px | 报告正文、转写 |
| `--fs-body-sm` | 14px / 20px | 界面正文、按钮 |
| `--fs-label` | 13px / 18px | 标签、chip（大写标签字距 0.08em） |
| `--fs-caption` | 12px / 16px | 注释、窗口路径 |

## 3. 间距、圆角、阴影

间距：`--space-1` 4 · `--space-2` 8 · `--space-3` 12 · `--space-4` 16 · `--space-5` 24 · `--space-6` 32 · `--space-7` 48 · `--space-8` 64。手机两侧固定 16。

圆角：`--radius-sm` 6（chip）· `--radius-md` 10（按钮、输入框）· `--radius-lg` 16（卡片、面板、窗口）· `--radius-full` 999（通话按钮、胶囊）。

阴影：`--shadow-1` `0 1px 2px var(--shadow-color)`，只给蓝色舞台上的摄像头小窗；`--shadow-2` `0 12px 32px var(--shadow-color)`，只给浮层。卡片不加阴影。

动效：`--dur-fast` 120ms · `--dur` 200ms。音波、呼吸圈、连接中的转圈在 `prefers-reduced-motion` 下全部关闭，文字状态保留。

## 4. 组件

**按钮**（字号 `--fs-body-sm` 600，圆角 `--radius-md`）
- Primary：高 48（首页、Setup 底部）或 40，底 `--color-blue`，白字，hover `--color-blue-hover`。每屏只有一个。
- Secondary：白底，1px `--color-border-strong`，墨色字。
- Ghost：无底无边，字 `--color-blue-text`，hover 底 `--color-tint`。
- 焦点：`outline: 2px solid var(--color-blue); outline-offset: 2px`。

**转写面板**（首页招牌）：底 `--color-tint`，圆角 `--radius-lg`。每一轮 = 说话人 + mono 时间戳 + 文字。面试官普通提问：白底气泡；你的回答：无底，墨色；**追问**：整块 `--color-blue` 底、白字 `--fs-lead`，顶部写 "Follow-up"，配 12 根白色音波条。

**赛道卡片**：本质是单选框。未选：白底，1px `--color-border`，圆角 `--radius-lg`。选中：整卡填 `--color-blue`，文字和图标变白，右上角白色圆形勾。三张等宽，手机上纵向堆叠。

**Chip**：高 24，圆角 `--radius-sm`，`--fs-label` 500。成功 / 警告 / 中性（`--color-tint` 底）/ "Not measured"（白底 + 虚线边框 + 辅助色字）。

**时间戳 Chip**：`--font-mono` + `tabular-nums`，底 `--color-tint`，字 `--color-blue-text`，左侧小三角；hover 或当前选中时整块变 `--color-blue` 白字。区间写作 `3:02–3:40`。

**电平表**：20 格，亮格 `--color-blue`，最后 3 格（过载）用 `--color-warning`，未亮格 `--color-tint-strong`。

**面试舞台（Live）**：整块蓝色面板，从 `--color-blue` 到 `--color-blue-deep` 自上而下轻微过渡（全站唯一允许的渐变）。问题文字 `--fs-display-l` 白色；面试官标志是白色细圈加音波图标。状态胶囊底 `--color-on-blue-veil`：
- Connecting…：圈变虚线慢转，问题区显示 "Connecting to your interviewer"，计时器停在 00:00。点完 Setup 的 "Start interview" 直接进入这个状态，没有第二个开始按钮。
- Speaking：胶囊里 5 根音波条跳动。
- Listening：外圈缓慢呼吸，带一个绿色小点。
- Thinking：3 个点依次变亮。

**通话控制栏**：在深蓝底上，只有两个按钮。Mute：48px 圆形，透明底 + `--color-on-blue-veil` 边框，白色图标；静音后变白底、墨色划线麦克风，文字变 "Unmute"。End interview：白色胶囊，`--color-danger` 文字和图标。

**会话时间轴**（报告骨架）：`--color-tint` 面板，宽屏时吸顶。从上到下：播放按钮（蓝色圆）+ mono 时间；一条分成 Q1–Q4 的条带（`--color-tint-strong` 与白交替，段内标 Q1 等）；条带上方是蓝色编号圆点 1/2/3（对应 3 件要改的事），条带下方是蓝色小刻度（其他证据）；墨色播放头竖线。点编号、刻度或任何时间戳 chip，播放头跳过去；点编号同时展开对应条目。

**报告条目**：编号是 28px 蓝色方块加白色 display 数字，和时间轴编号一一对应。标题（一句可执行的话）+ 时间戳 chip；展开后是引用块（`--color-tint` 底，不加左侧色条）和 "Try" 改法。指标行：左列名称，中间 mono 大数字带单位 + 解释，右列状态 chip。

## 5. 规则

1. 每屏只有一个 Primary 按钮。
2. 不用 emoji，图标统一为 1.6px 线性 SVG。
3. 不用彩虹/多色渐变。唯一的渐变是面试舞台的蓝到深蓝。
4. 不用卡片墙加阴影。分组靠间距和 1px 分隔线。
5. 指标数字一律 `--font-mono` + `tabular-nums`，并带单位：`168 wpm`、`4.3 s`、`74%`、`24 dB`。
6. 每条反馈必须有时间戳 + 原话，或时间戳 + 测量值。
7. 测不到就写 "Not measured" 并说明原因，不打低分、不显示 0。
8. 面试中不显示分数。报告里总分只在元信息里占一行。
9. 文案不推断情绪（不出现 nervous、confident）。
10. 文案用平实英语，按钮写动作，不用破折号。
11. 只做浅色。`body` 明确设 `background: var(--color-bg)`，`:root` 设 `color-scheme: light`。

## 6. 落地到代码

- `src/index.css` 的 `:root` 换成本文变量（演示文件 `<style>` 顶部的 `:root` 可以整段复制）。
- `src/App.css` 删除 `--monet-*`、Playfair/Outfit、`.hero-bg-orbs`、所有 `linear-gradient`（面试舞台那一处除外）。
- 原来 4 步的"选级别 / 加资料 / 选模式"合并成一屏 Setup。**级别（年龄段）整项删掉**；More options 只留 Length 和 Notes for the interviewer。
- 简历只收 PDF：`accept=".pdf"`。
- Setup 点 "Start interview" 后直接进入面试页的 Connecting 状态并自动开始，不再出现第二个开始按钮。

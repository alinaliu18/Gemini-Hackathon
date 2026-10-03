# Product polish spec（一周）

> 分支 `product-polish`。依据：README、`src/App.jsx`、`src/components/*`、`src/live/liveSession.js`、`backend.py`、`pipeline/`，以及 Obsidian《黑客松升级方案-多模态》。流程已定，本文只把它写成能开工、能验收的规格。
> 文案规则：UI 文案全英文，大白话，不用破折号，不用感叹号，不用 emoji。

---

## 1. 定位与首页 headline

**一句话定位**：给要去面试的学生用的语音模拟面试。AI 面试官按你的简历提问，跟着你刚说的话追问；结束后给一份改进清单，每一条都指到录音里的时间点和原话，或者一个测出来的数（语速、停顿、嗯啊、看镜头）。

| # | Headline 候选 | 副标题（共用） |
|---|---|---|
| A | **Practice out loud with an interviewer who follows up.** | It asks about your resume, follows up on what you say, then shows you the exact moments to work on. |
| B | Mock interviews that show you the exact moment to fix. | 同上 |
| C | Say it out loud before it counts. | 同上 |

**推荐 A。** 首页唯一的动作是"开始说话"，A 直接说了这件事（out loud）和别家没有的东西（会追问）。B 卖的是报告，但用户在首页还没到报告那一步。C 好记，可没说产品做什么，从 GitHub 点进来的人看不懂。"有证据的报告"放副标题里讲。

---

## 2. 页面规格

### 2.0 共通

- 顶栏：左边产品名 `Interview Maestro`（点了回首页），右边什么都不放。面试中隐藏顶栏。
- 时间戳统一用 `m:ss`（如 `1:42`）。
- 只在面试中和生成报告时拦截离开：`beforeunload` 提示浏览器默认文案。

### 2.1 Landing（首页）

**目的**：一句话讲清楚这是什么，让人点主按钮。

| 从上到下 | 英文文案 |
|---|---|
| Headline | `Practice out loud with an interviewer who follows up.` |
| 副标题 | `It asks about your resume, follows up on what you say, then shows you the exact moments to work on.` |
| **主按钮** | `Start mock interview` |
| 按钮下一行小字 | `Free. No sign-up. About 6 minutes.` |
| 三步条 | `1  Drop your resume` / `Optional. The interviewer asks about your real experience.` |
| | `2  Pick an interview type` / `Academic, Career or Social.` |
| | `3  Talk it through` / `Answer out loud. Get a report that points to the exact moments.` |
| 次要链接 | `Or practice a single question` → Quick Practice |
| 页脚 | `Your video stays on this device. Only numbers are sent.` · `How it works`（链 GitHub README）· `GitHub` |

- 页面加载时后台发一次 `GET /api/health`，用来唤醒 Cloud Run（冷启动），用户看不到。
- 手机或非 Chrome 浏览器：主按钮上方一条提示 `Works best in Chrome on a computer.`，不拦。

### 2.2 Setup（一屏）

**目的**：30 秒内准备好并开始。只有面试类型是必选。

| 从上到下 | 英文文案 |
|---|---|
| 标题 | `Set up your interview` |
| 说明 | `Takes about 30 seconds.` |
| **区块 1：简历** 标题 | `Resume (optional)` |
| 拖放区 空状态 | `Drop your resume here or browse` / `PDF, up to 5 MB.` |
| 拖放区下方说明 | `No resume? Skip this. You'll get general questions for the type you pick.` |
| 读取中 | `Reading your resume` |
| 读取成功 | `{filename} · Ready`，右侧链接 `Remove` |
| **区块 2：面试类型** 标题 | `Interview type` |
| 卡片 Academic | `Academic` / `College, scholarship and grad school interviews` |
| 卡片 Career | `Career` / `Internships and job interviews` |
| 卡片 Social | `Social` / `Clubs, student orgs and volunteer roles` |
| **区块 3：麦克风和摄像头** 标题 | `Mic and camera` |
| 未检查 | 按钮 `Check mic and camera` |
| 检查中 | 自己的摄像头小预览 + 音量条，`Say something. The bar should move.` |
| 麦克风正常 | `Mic is working` |
| 摄像头开关 | `Use camera`（默认开）|
| 摄像头开 | `Camera is on. It only measures where you look, on this device.` |
| 摄像头关 | `Camera is off. Eye contact won't be measured.` |
| 耳机提示 | `Use headphones so the interviewer doesn't hear itself.` |
| **More options**（默认折叠） | 折叠标题 `More options` |
| 年级 | 标签 `Your level`，下拉：`Not set` / `Middle school` / `High school` / `College` / `Early career` / `Mid career` / `Senior`，默认 `Not set` |
| 补充信息 | 标签 `Job description or notes`，占位 `Paste a job description, the role you're applying for, or questions you want to practice.` |
| 按钮上方一行 | `About 3 questions with follow-ups. 5 to 8 minutes.` |
| **主按钮** | `Start interview`（没选类型时禁用，下方小字 `Pick an interview type to start.`）|
| 次要 | `Back` |

- 没点过 "Check mic and camera" 就点 Start：直接在这一步申请权限，拿到麦克风就继续，不让用户多点一次。
- 简历一放下就调后端解析（见第 6 节 `/api/resume`），出错在这一屏就提示，不等到面试开始。
- 临时 token 在点 Start 时才去拿（token 规定 2 分钟内必须开始会话，`pipeline/live.py`）。

### 2.3 Live interview（像视频通话）

**目的**：让人专心说话，屏幕上只留必须的东西。

| 位置 | 内容 / 英文文案 |
|---|---|
| 左上 | `{Type} interview` · 计时 `3:12` |
| 中间大块：面试官 | 圆形头像 + 名字 `Interviewer` + 状态：`Connecting` / `Speaking` / `Listening` |
| 面试官下方：字幕一行 | 只显示面试官**当前这句话**（不显示用户自己的实时转写，见 Open question 2） |
| 右下小窗：你 | 自己的摄像头；摄像头关时显示 `Camera off` |
| 底栏（只有两个） | `Mute` / `Unmute`，`End interview` |
| 静音时横条 | `You're muted. The interviewer can't hear you.` |
| 9:00 时横条 | `1 minute left. The interview will end at 10:00.` |
| 点 End 弹窗 | 标题 `End the interview?` / 说明 `You'll get a report on what you've said so far.` / 按钮 `End and get report`（主）、`Keep going` |

- 面试官说完结束语（"report is being prepared"）自动进入生成报告，不用点。
- 10:00 自动结束并生成报告（硬上限，见第 6 节）。
- Mute = 关掉麦克风音轨（`track.enabled = false`），Live 和录音都收不到声音。
- Speaking / Listening：有面试官音频在播放就是 Speaking，否则 Listening。`liveSession.js` 需要加一个 `onSpeaking(bool)` 回调。

### 2.4 Report（读起来像一份文档）

**生成中**（同一页面的加载态）

| 从上到下 | 英文文案 |
|---|---|
| 标题 | `Writing your report` |
| 进度条 | 按时间填到 90%（约 60 秒），返回后补满 |
| 步骤（按时间依次打勾） | `Saving your recording` → `Writing down what you said` → `Measuring pace, pauses and filler words` → `Linking each point to the moment it came from` |
| 说明 | `This usually takes under a minute. Keep this tab open.` |
| 90 秒还没好 | `Taking longer than usual. Still working.` |
| 等待时的内容 | `Questions you were asked`：列出面试官问过的问题（前端已有 turns，不用等后端）|

步骤是按后端实际顺序写的，但打勾时间是估的（后端是一个请求，没有真实进度）。

**报告页**

| 从上到下 | 英文文案 |
|---|---|
| 标题 | `Interview report` |
| 元信息一行 | `{Type} interview · {Oct 2, 2026} · {6 min 40 s} · Overall {72}/100` |
| 部分评分提示（覆盖率 < 80% 时） | `Partial score. Not measured: {eye contact, presence}.` |
| 录音播放条（吸顶） | 标签 `Your recording` |
| **区块：Top 3 things to fix** | 每条：序号 + 一句话问题 + `Try: {tip}`；折叠按钮 `Show where` / `Hide` |
| 展开后 | 每条证据一行：时间按钮 `Play 1:42` + 原话 `"{quote}"` 或测得的信号 `{Paused 4 s}` |
| 少于 3 条时 | 标题改成 `Things to fix`，有几条显示几条，不凑数 |
| 0 条时 | `Nothing stood out with enough evidence to flag. See the details below.` |
| **What went well** | 同样结构，带证据 |
| **Question by question** | 每题一个折叠块：`Q1 · 0:12 · {question}`，右侧 `{score}`；全部默认折叠 |
| **Delivery** | Pace / Pauses / Filler words / Eye contact / Presence，每项：测得的数 + 一句观察 + 证据；测不了的写 `Not measured: {reason}` |
| **Transcript** | 默认折叠，每段前面有时间按钮 |
| 页脚说明 | `This report isn't saved. Download it before you close this tab.` |
| **主按钮** | `Start another interview` |
| 次要 | `Download PDF`（`window.print()` + 打印样式）、`Back to home` |

维度名改成白话：`Structure (STAR)` → `Structure`；`rubric` 一词不出现。

### 2.5 Quick Practice（次要入口）

**目的**：只练一道题。保留现有功能，换成和新流程一致的样式。

| 从上到下 | 英文文案 |
|---|---|
| 标题 | `Practice one question` |
| 类型 | 三选一小分段控件 `Academic` / `Career` / `Social` |
| 简历 | 一行 `Add resume (optional)`，复用 Setup 的解析 |
| 题目卡 | 标签 `Your question`，加载中 `Writing a question`，链接 `New question` |
| 回答 | 按钮 `Record answer` / `Stop`；下方链接 `Type instead` 展开文本框，占位 `Type your answer here.` |
| **主按钮** | `Get feedback`（没录音也没文字时禁用）|
| 结果 | 复用 2.4 的报告版式（只有一题），按钮 `Try again`（主）、`Try a full interview`、`Back to home` |

---

## 3. 状态与错误提示

| 状态 | 触发条件 | 提示（英文） | 用户下一步（英文按钮/文案） |
|---|---|---|---|
| 加载中：唤醒后端 | 任何后端请求 3 秒没回 | `Waking up the server. This can take a few seconds.` | 自动等待，前端自动重试 1 次 |
| 加载中：读简历 | 简历上传中 | `Reading your resume` | 等待；可点 `Remove` 取消 |
| 加载中：连接面试官 | 点 Start 到收到 setupComplete | `Connecting to your interviewer` | 等待（实测 2.4 到 3.5 秒） |
| 生成报告中 | 结束面试后，`/api/session_report` 处理中（实测 32 到 64 秒） | 见 2.4：4 步打勾 + 进度条 + `This usually takes under a minute. Keep this tab open.`；超过 90 秒 `Taking longer than usual. Still working.` | 等待；180 秒超时转"后端没响应" |
| 麦克风被拒 | `getUserMedia` 报 `NotAllowedError` | `Your microphone is blocked. The interviewer needs to hear you.` | `Click the lock icon in the address bar, allow Microphone, then try again.` 按钮 `Try again`；链接 `Practice by typing instead`（去 Quick Practice） |
| 没有麦克风 | `NotFoundError` | `We can't find a microphone.` | `Plug one in or check your system settings.` 按钮 `Try again` |
| 摄像头被拒 | 视频权限被拒，音频成功 | `Camera is off. You can still do the interview. Eye contact won't be measured.` | 不拦，`Start interview` 照常可点 |
| 没检测到人脸 | 检查时 3 秒内人脸检测一直为空 | `We can't see your face. Face the camera and make sure the room is lit.` | 不拦，可直接开始；报告里该项标 `Not measured` |
| 后端没响应 | fetch 抛 TypeError、5xx、或请求超时（token 15 秒，报告 180 秒） | `We can't reach our server right now.` | `Try again in a minute.` 按钮 `Try again`。报告失败时录音还在页面内存里，按钮为 `Try the report again`，不用重新面试 |
| 没识别到说话：检查时 | 音量条 5 秒没动 | `We can't hear you. Check that the right mic is selected and not muted.` | 不拦，按钮 `Check again` |
| 没识别到说话：报告 | 后端返回 `summary: null`（"No answers found in the recording."） | `We didn't hear any answers, so there's nothing to report.` | `Check your mic, then start a new interview.` 按钮 `Start another interview` |
| 实时连接断开 | WebSocket 非主动关闭（`onclose` 且未调 stop） | `The connection to the interviewer dropped.` | 按钮 `Get report for what you said`（主，用已录部分出报告）、`Start over` |
| 会话快超时 | 收到 `goAway` | `The session is about to time out. The interview will end soon.` | 无操作，到点自动出报告 |
| 简历解析失败 | 非 PDF、超过 5 MB、PDF 读不出文字（扫描件，提取文字 < 100 字符）、解析异常 | `We couldn't read text from this file.` | `Try a different PDF, or skip it and get general questions.` 按钮 `Remove`；Start 照常可点 |
| 达到每日次数上限（单 IP） | 后端返回 `429` + `{"error": "daily_limit"}` | `You've used today's 5 free interviews.` | `Come back tomorrow. It resets at midnight Pacific time.` 链接 `Practice a single question`（单独计数） |
| 达到全站上限 / Gemini 额度用完 | 后端返回 `429` + `{"error": "busy"}`（全站日上限，或所有 key 都 429） | `We're at capacity right now.` | `Try again later today.` |

注意：现在 `/api/live/token` 在所有 key 都 429 时也返回 429，要和"每日上限"用 `error` 字段分开，否则用户会看到错的提示。

---

## 4. 砍掉或移走的东西

| 现在有的 | 去向 |
|---|---|
| 首页全屏 hero 的光球、流星、闪光、滚动箭头、滚动出现动画 | 删 |
| 标题 `Interview / Interview Maestro` 双行、`AI-Powered Interview Preparation`、`Practice smarter. Perform better. Land your dream opportunity.` | 删，换成第 1 节 headline |
| 首页 `Choose Your Path` 三张赛道卡（带 emoji 和标签） | 移到 Setup 区块 2，去掉 emoji 和标签，各一行说明 |
| 第 1 步年级选择（6 张卡、年龄段） | 移到 More options 的 `Your level` 下拉，可选 |
| 第 2 步简历和文本框之间的 `OR` | 删；文本框移到 More options |
| 三步进度条 `1-2-3` | 删 |
| 第 3 步 `Choose Practice Mode`（两张模式卡、Recommended 标、功能列表） | 删。Live 是默认路径，Quick Practice 是首页次要链接 |
| Live 页的 `Use camera...` 勾选框、摄像头说明、耳机提示、"About 3 questions..." | 移到 Setup |
| Live 页全量字幕面板（双方实时转写） | 换成面试官当前一句；完整转写在报告 `Transcript` |
| Live 页 `Ready / Connecting… / Interview in progress` 状态条 | 换成面试官状态 `Connecting / Speaking / Listening` |
| Live 页 `← Back` | 删，只留 Mute 和 End |
| 报告的大号总分 | 缩到标题下元信息一行 |
| 报告 `Whole interview` 里每个维度的分数列表 | 移到下方 `Delivery` 区块 |
| 报告第一题默认展开 | 全部默认折叠 |
| 所有 emoji（🎓🤝💼📚📊✨⏳🔄🏠🎥🎙️🎤✍️⚠️ 等） | 删 |
| 维度名 `Structure (STAR)`，提示里的 `rubric` | 改 `Structure`；`Partial score. Not measured: ...` |
| `public/camera.html`（队友原型） | 新流程不链接；文件保留，README 保留署名 |

---

## 5. 验收标准

### Landing
- [ ] 首屏（1280×720）不滚动就能看到 headline、主按钮、三步条、Quick Practice 链接
- [ ] 页面上只有一个主样式按钮
- [ ] 打开页面即发出 `/api/health`（Network 面板可见）
- [ ] 375 px 宽无横向滚动
- [ ] 无 emoji、无动画装饰、无感叹号、无破折号

### Setup
- [ ] 只选类型、不放简历、不开 More options，能直接 Start
- [ ] 放入扫描件 PDF 和 .docx，都在本屏显示简历解析失败提示，且仍能 Start
- [ ] 不点检查直接 Start，浏览器弹权限，同意后直接进面试
- [ ] 拒绝摄像头、允许麦克风，能开始面试，报告里眼神项为 `Not measured`
- [ ] 拒绝麦克风，显示对应提示和 `Practice by typing instead`
- [ ] More options 默认折叠；填了 level 和 notes 后，面试官问题能体现（至少 1 题提到 notes 内容）

### Live interview
- [ ] 底栏只有 Mute 和 End
- [ ] 面试官说话时显示 `Speaking`，停下后 1 秒内变 `Listening`
- [ ] Mute 后说话，面试官没有反应，且显示静音横条
- [ ] 点 End 出确认框；选 `Keep going` 面试继续
- [ ] 面试官说结束语后自动进入生成报告
- [ ] 断网 5 秒，出现断开提示，`Get report for what you said` 能出报告
- [ ] 10:00 自动结束

### Report
- [ ] 生成中 4 个步骤依次打勾，`Questions you were asked` 立即可见
- [ ] 顶部最多 3 条要改的，每条展开后都有时间按钮和原话或信号值
- [ ] 点任一时间按钮，录音跳到该秒并播放，误差 ≤ 1 秒
- [ ] `Download PDF` 打出的 PDF 包含 Top 3 和证据
- [ ] 后端报告请求失败后，`Try the report again` 不用重新面试就能出报告

### "60 秒内开始说话"怎么测
- 定义：从首页加载完成，到用户第一次对面试官的提问开口（收到第一条 candidate `inputTranscription`）。
- 埋点：首页 `load` 时记 `performance.now()`，第一条 candidate 转写到达时 `console.info('time_to_first_answer_s', x)`。不上报，只在控制台。
- 测法：线上 Vercel 地址，Chrome 无痕窗口（权限未授予），桌面上放好一份 PDF 简历，先空闲 15 分钟让 Cloud Run 冷下来。跑 3 次，取中位数。
- 通过：中位数 ≤ 60 秒，且冷启动那次 ≤ 75 秒。Day 7 真人试用另记一次（见第 7 节）。

---

## 6. 部署要求

### 6.1 为什么后端放 Cloud Run

| 原因 | 事实 | 来源 / 把握 |
|---|---|---|
| 请求体太大 | Vercel 函数请求体和响应体上限 **4.5 MB**，超了返回 413。10 分钟录音按 32 到 128 kbps 算是 2.4 到 9.6 MB，高码率时会超。Cloud Run HTTP/1 单请求上限 **32 MiB**。 | Vercel 文档 Functions Limits（2026-08-24 更新）；Cloud Run quotas 文档。高。录音实际大小 Day 2 用真实录音量一次 |
| 需要 ffmpeg | 停顿检测和切分回答都调系统 `ffmpeg`（`pipeline/session.py`、`audio_metrics.py`）。容器里装一行就行，Vercel 函数里不方便。 | 代码。高 |
| 报告 32 到 64 秒 | **这一条不再成立**：Vercel 开 Fluid compute 后 Hobby 默认和上限都是 300 秒，64 秒放得下。所以时长不是放 Cloud Run 的理由，上面两条才是。Cloud Run 单请求最长 60 分钟。 | Vercel 文档同上；Cloud Run quotas 文档。高 |

### 6.2 上线配置

| 项 | 要求 |
|---|---|
| 前端（Vercel） | `API_BASE_URL` 从写死的 `http://localhost:5002` 改成 `import.meta.env.VITE_API_BASE` |
| 后端（Cloud Run） | Dockerfile：python + `apt-get install ffmpeg`；`gunicorn -b 0.0.0.0:$PORT --threads 8 --timeout 300 backend:app`（现在是 `127.0.0.1:5002`） |
| Cloud Run 参数 | 请求超时 300 秒；`max-instances=1`；`min-instances=0`，靠首页 health 请求预热 |
| 密钥 | `GEMINI_API_KEY(S)` 放 Secret Manager 注入环境变量，不进镜像、不进仓库 |
| CORS | 从 `*` 改成只允许 Vercel 域名（加本地 `localhost:5173`） |
| 上传上限 | Flask `MAX_CONTENT_LENGTH = 20 MB`；简历 5 MB 并只收 PDF |

`max-instances=1` 的理由：每日计数可以先放内存（实例重启会清零，可接受），同时也是费用上限。并发上来再换 Firestore 计数。

### 6.3 次数和时长上限

| 限制 | 默认值 | 理由 |
|---|---|---|
| 每 IP 每天 Live 面试 | **5 次**（按开始面试计，即 `/api/live/token`） | 一个学生一天练 1 到 2 次，留 1 次给麦克风出问题重来；校园和社团活动常共用一个出口 IP，3 次会误伤。按单场约 $0.3 上限算，单 IP 每天最多约 $1.5 |
| 每 IP 每天 Quick Practice | 20 次（按 `/api/evaluate` 计） | 单题便宜（一次转写 + 一次解读），主要防脚本刷 |
| 全站每天 Live 面试 | **50 次**（环境变量 `GLOBAL_DAILY_CAP`，设 0 即关停） | 每天最坏约 $15。是唯一真正的刹车，见 6.4 |
| 单场面试时长 | **10 分钟**，9:00 提醒，10:00 自动结束 | README：纯音频 Live 会话上限 15 分钟，单条连接约 10 分钟，还没做会话续接 |
| 计数重置 | 每天 0 点 Pacific 时间 | 用户在 UCLA |
| IP 取法 | `X-Forwarded-For` 第一个地址 | Cloud Run 在代理后面 |

### 6.4 预算提醒

**单场费用估算**（把握：中。Live 会话里上下文每轮怎么计费，官方定价页没写）：

| 部分 | 算法 | 约 |
|---|---|---|
| Live 输入音频 | 10 分钟 × $0.005/分钟（gemini-3.8-live） | $0.05 |
| Live 输出音频 | 面试官说 2 到 3 分钟 × $0.018/分钟 | $0.05 |
| 报告：转写 | 约 8 分钟回答 × 1,920 token/分钟 × $1.00/百万（gemini-2.5-flash 音频输入） | $0.02 |
| 报告：解读 | 4 到 5 次文本调用，输入 $0.30/百万，输出 $2.50/百万 | $0.04 |
| **合计** | | **约 $0.15，按 $0.3 留余量** |

来源：ai.google.dev Gemini API pricing；音频 32 token/秒 来自 Gemini audio understanding 文档。Day 3 跑 5 场后用账单实际数校准。

- Google Cloud Billing 建预算 **$30/月**，在 50%、90%、100% 发邮件。
- **预算只提醒，不会自动停**（官方原话："alerts-only budget doesn't automatically cap ... usage or spending"）。真正的刹车是 `GLOBAL_DAILY_CAP`；收到 100% 提醒就把它设成 0。
- 公开链接要用付费层 key，原因见 Open question 5。

### 6.5 后端改动清单（工程按这个排）

| 改动 | 位置 |
|---|---|
| 新增 `POST /api/resume`：只收 PDF ≤ 5 MB，返回 `{ok, pages}` 或 `{error}`；提取文字 < 100 字符算失败 | `backend.py` |
| `extract_text_from_pdf` 失败时现在会把 `"Could not read PDF: ..."` 当简历内容塞进 prompt，改成抛错 | `backend.py` |
| 每 IP / 全站计数，429 带 `error: daily_limit` 或 `busy` | `backend.py` |
| 总结从 top 2 改成 top 3 要改进项（现在是 `improvements[:2]`） | `pipeline/session.py` |
| `age_group` 传进面试官指令（现在前端传了，后端一处都没读） | `pipeline/live.py`、`backend.py` |
| `onSpeaking` 回调，断线时保留已录内容可出报告 | `src/live/liveSession.js`、`LiveInterview.jsx` |

---

## 7. Day 7 真人试用

**找谁**：2 到 3 人。至少 1 个没见过这个产品的学生，至少 1 个社团面试官。各自用自己的电脑和 Chrome。

**给他们的一句话**（英文版和中文版，看对方习惯）：
> `Here's a link. Do a practice interview for something you're actually applying to. Please think out loud while you set it up.`
> 「这是链接。就当你真要去面试某个东西，做一次模拟面试。准备阶段请边做边说你在想什么。」

不解释产品，不帮忙，卡住超过 30 秒再问"你在找什么"。

**观察什么**

| 阶段 | 记录 |
|---|---|
| 首页 | 是否直接点主按钮；有没有去点 Quick Practice |
| Setup | 计时；在哪停顿（简历、类型、权限）；有没有打开 More options |
| 开始说话 | 用秒表记 time to first answer，和控制台埋点对一下 |
| 面试中 | 有没有找 Mute/End；被面试官抢话几次；有没有说"它没听懂" |
| 等报告 | 有没有看 `Questions you were asked`；有没有切走标签页 |
| 报告 | 有没有不经提示就点时间按钮；先看哪一块；有没有往下翻到 Delivery |

**结束后问 3 个问题**
1. 「下次回答你会改哪一件事？这条是从报告哪里看出来的？」（检验报告能不能照着改、证据有没有被看到）
2. 「有没有哪一刻你不知道该干什么，或者觉得不舒服？」（检验流程卡点和压力）
3. 「真要面试前你会再用它吗？什么情况下不会？」

**通过线**：至少 2 人 60 秒内开口；至少 2 人能说出一条要改的事并指出对应的时间点或原话。

---

## 8. Open questions（需要产品负责人拍板）

| # | 问题 | 我的推荐 |
|---|---|---|
| 1 | 报告里要不要显示总分？原始痛点之一是视觉压力，大号分数会加压 | 保留分数，但缩到标题下元信息一行，不做大字 |
| 2 | 面试中显示多少字幕？ | 只显示面试官当前一句（照顾听力和非母语用户），不显示自己的实时转写（看着自己的话被转写会分心、加压）。完整转写放报告 |
| 3 | 后端总结目前只出 2 条改进，流程要 3 条。证据校验后不够 3 条怎么办？ | 改成最多 3 条；不够就显示实际条数，不凑数 |
| 4 | 每 IP 每天 5 次、全站 50 次够不够？ | 先按这个上线，Day 7 看社团现场是否共用 IP 被挡，再调。全站上限按你能接受的月预算倒推 |
| 5 | 用免费层还是付费层 Gemini key？免费层条款写明会用提交内容改进产品，且可能有人工审阅；这里传的是真实学生的简历和声音 | 公开链接用付费层 key；本地开发可以用免费层 |
| 6 | `Your level` 现在后端完全没用到。保留在 More options 就得接进面试官指令 | 接进去（一行改动），让它真的影响问题难度；不接就直接删掉，别留一个没用的选项 |
| 7 | 简历只收 PDF，还是加 DOCX？现在 UI 写着收 DOC/DOCX，后端只会读 PDF | 这周只收 PDF，文案写清楚 |
| 8 | 报告要不要保存（刷新就没了）？ | 这周不存。不做账号，也不在服务器留学生录音；给 `Download PDF` |
| 9 | 手机和 Safari 要不要支持？README 写了只在 Chrome 测过，Safari 可能拦音频 | 这周不支持，只提示 `Works best in Chrome on a computer.`，不拦 |
| 10 | Cloud Run `min-instances` 设 0 还是 1？0 省钱但有冷启动，可能吃掉 60 秒目标 | 先设 0 + 首页预热。Day 2 测冷启动，超过 10 秒就在演示周设成 1 |
| 11 | 产品名保留 `Interview Maestro`？ | 保留，这周不改名 |

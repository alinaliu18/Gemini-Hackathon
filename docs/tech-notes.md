# 技术说明

面试里最容易被追问的 3 件事，流式报告、key 轮换和模型回退、存储。每一节先写为什么要这么做，再写代码在哪、怎么做的，最后给一句英文，英文面试可以直接说。

只写实测过的数字。没测过的地方都标了「还没测」。

---

## 1 流式报告，为什么等待从 32 到 64 秒变成 9 到 15 秒

### 问题是什么

一场面试大约 3 个回答。原来的做法是整段录音一次转写完，再一次解读完，最后把整份报告返回给前端。实测等待 32 到 64 秒。这个长度的空白页，用户会切到别的标签页去，回来就不记得自己刚才说了什么，报告的价值也就没了。

### 做了 3 件事

**1 关掉 thinking。** 在 `pipeline/config.py` 的 `THINKING_BUDGET` 里，转写和解读都设成 0。转写是听写，本来就不需要推理。解读输出的是结构固定的 JSON，字段都是定好的，也不需要。这个设置只对 gemini-2.5 系列生效，回退模型自己决定要不要思考。

**2 每个回答一条线程。** 在 `pipeline/session.py` 里，录音按面试官提问的时间切成一段一段，第 i 个回答是从第 i 个问题说完，到第 i+1 个问题开始。每一段用 ffmpeg 单独切出来，单独转写，单独解读。短回答不用排在最慢那一段后面。整场总结只等所有转写完成，不等每一条解读完成。

切成短片段还有一个额外好处，Gemini 在长录音上给的时间戳会漂，开头有静音时尤其明显。短片段的时间戳准，再把偏移量加回去，就回到整场的时间轴上。报告里每条评语能点回录音的某一秒，靠的就是这个。

**3 边做边推。** `/api/session_report/stream` 返回 ndjson，一行一个 JSON。事件顺序是 `stage` 说一共几个回答，`transcribed` 报转写进度，`answer` 每出一条回答的反馈就推一条，`summary` 推整场总结，最后 `done` 带完整报告，出错就推 `error`。前端在面试一结束就打开报告页，哪条先回来就先画哪条。

### 结果

同一份合成的 3 问面试，29.5 秒降到 9 到 15 秒。

这是一次测试的范围，不是平均值。Gemini 自己的延迟每次波动很大，赶上高峰会更慢。说数字的时候要带上这句，不然被追问「你测了几次」会很难看。

`tests/test_session_stream.py` 离线检查事件顺序和并行，不打真 API。

### 被追问怎么答

**为什么不用 SSE 或者 WebSocket。** 这个请求要带录音上传，是 multipart 的 POST。浏览器的 EventSource 只能发 GET，用不了。前端本来就用 fetch 读响应流，一行一个 JSON 自己就够用，不用再引一层协议。

**为什么用线程不用 asyncio。** 两个阻塞点，一个是 Gemini SDK 的同步调用，一个是 ffmpeg 子进程。一场面试 3 到 4 个回答，线程数很小。代码注释里写了，如果以后一场面试问题变多，要给线程池加上限。

**连接中途断了怎么办。** 前端会显示报告没拿完并给重试。报告本身在后端是算完就写进 SQLite 的，带 `run_id`，没丢。

**英文怎么说。** The report used to arrive in one 32 to 64 second block. I turned thinking off for both model calls, ran each answer on its own thread, and streamed the report as newline delimited JSON, so the page opens immediately and fills in. On one synthetic 3 answer interview that took it from 29.5 seconds to 9 to 15.

---

## 2 key 轮换和模型回退，为什么要做

### 问题是什么

免费层大约是一个 key 一个模型一天 20 次请求，一份报告要用掉大约 7 次。现场演示跑两遍就没额度了。另外 Gemini 高峰期会返回 503，模型下线会返回 404。这两种情况都不该让用户看到一个报错页。

### 怎么做的

`backend.py` 里的 `with_client` 包住每一次模型调用，两层循环。外层是模型，先主模型 gemini-2.5-flash，再依次是 gemini-flash-latest 和 gemini-3.5-flash-lite。内层是 key。

分成两类处理，这是整段代码的核心判断。

**429 或者 RESOURCE_EXHAUSTED 是额度问题**，跟模型没关系，所以换下一个 key，模型不变。

**503、UNAVAILABLE、404、NOT_FOUND 是模型问题**，这个模型对所有 key 都是一样的，所以不浪费时间试别的 key，直接跳到下一个模型。

**其他错误直接抛出去，不吞。** 这一条最重要。参数写错、JSON 格式错，如果也被当成额度问题去重试，真正的 bug 会被藏起来，表现成「变慢了」而不是「报错了」。

还有一个细节，SDK 自带的重试在 503 上会退避等大约 2 分钟。用户不可能等。所以把 `attempts` 设成 2，剩下的交给换模型。

Live 面试的 token 是另一条路径，用 v1alpha，只轮换 key，不换模型，因为模型已经锁死在 token 里了。

`tests/test_fallback.py` 用假的调用检查这个顺序，不打真 API。

### 被追问怎么答

**为什么不在前端重试。** key 不能进浏览器。浏览器拿到的是后端铸的一次性 token，30 分钟内有效，2 分钟内必须开始会话，模型和面试官的 system instruction 都锁在 token 里，前端改不了。这样 key 不出服务器，面试官的指令也不会被人在控制台改掉。

**轮换 key 算不算绕开限额。** 这是免费层开发用的。公开上线要用付费层 key，原因是免费层条款写明会用提交内容改进产品并且可能有人工审阅，而这里传的是真实学生的简历和声音。这条写在 `docs/product-polish/spec.md` 的 Open question 5。

**英文怎么说。** Every model call goes through one wrapper. A 429 means that key is out of quota, so it moves to the next key on the same model. A 503 or a 404 means the model is down or retired, so it skips straight to the next model. Anything else is raised, because retrying a real bug just hides it.

---

## 3 存储，为什么是这样设计的

### 问题是什么

黑客松那条分支没有存储。在那上面跑过的面试全丢了。现在 `data/maestro.db` 里只剩 10 月 4 日的 2 条短记录，内容还是 No answers found。没有数据，就没法回答「做得怎么样」「哪一步最慢」「哪一类问题分最低」。

### 怎么做的

`pipeline/store.py`，一个 SQLite 文件加一个 `audio` 目录，都在 `data/` 下面。

**分两次写，这是关键。** `start_run` 在任何模型调用之前写输入，`finish_run` 在结束时写输出，或者写错误。所以模型调用挂了，输入还完整留着，可以重跑，也能看到错误是什么。

**存什么。** 面试方向、补充信息、简历文本、面试官每一轮的内容和时间、摄像头算出来的数字、录音路径、完整报告 JSON、分数、错误、各个阶段的耗时。

**不存什么。** 视频。摄像头的画面只在浏览器里算，出去的只有数字，比如面向镜头 74%。

### 被追问怎么答

**为什么是 SQLite 不是 Postgres。** 单机、只有一个写入方、量级是几百条。一个文件，零运维，`python -m pipeline.store` 直接看最近 10 条。等真有并发写入再换，现在换是提前付成本。

**为什么输入输出分两次写，不一次写完。** 因为最容易失败的就是中间那段模型调用。一次写完等于失败就什么都没有，而失败的那些恰恰是最该看的。

**隐私怎么处理。** `data/` 在 gitignore 里，真人的录音和简历不进仓库。`MAESTRO_DATA_DIR` 换目录，`STORE_AUDIO=0` 只留文字。公开上线之前还差一句同意声明和一条保留期限，因为这里存的是真人的声音和简历。这件事没做完，要说清楚是没做完，不要说已经处理好了。

**英文怎么说。** Each run is written twice, the input before any model call and the output or the error when it ends, so a failed run still leaves everything needed to rerun it. It is one SQLite file because there is one writer and a few hundred rows. Video never reaches it, only numbers measured in the browser.

---

## 4 数字从哪来

说数字之前先看这张表。不在表里的数字就是没测过，不要说。

| 数字 | 测的是什么 | 在哪 |
|---|---|---|
| 32 到 64 秒 | 改之前，整场报告的等待时间，7 次无头浏览器运行 | README 的 Live interview 一节 |
| 29.5 秒降到 9 到 15 秒 | 改之后，同一份合成的 3 问面试 | README 的 Report speed 一节 |
| 单题端到端 25 到 31 秒 | eval 跑两个合成样本 | `eval/report.md` |
| 转写 4 到 10 秒 | 内联音频转写 | README |
| 开场问题 0.9 到 1.3 秒 | gemini-3.8-live，6 次运行 | README |
| 免费层一天约 20 次，一份报告约 7 次 | 配额，不是实测，是文档加推算 | README |

**还没测的。** 真麦克风跑完整一场面试、真实用户、上线以后的延迟、人工评分和模型评分的一致性。README 的 Known limitations 里写了这些，面试被问到要照这个说。

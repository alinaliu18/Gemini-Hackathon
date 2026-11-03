# 技术说明

面试里最容易被追问的 3 件事，流式报告、key 轮换和模型回退、存储。每一节先写为什么要这么做，再写代码在哪、怎么做的，最后给一句英文，英文面试可以直接说。

只写实测过的数字。没测过的地方都标了「还没测」。

---

## 1 流式报告，为什么等待从 32 到 64 秒变成 9 到 15 秒

### 问题是什么

一场面试大约 3 个回答。原来的做法是整段录音一次转写完，再一次解读完，最后把整份报告返回给前端。实测等待 32 到 64 秒。这个长度的空白页，用户会切到别的标签页去，回来就不记得自己刚才说了什么，报告的价值也就没了。

### 做了 3 件事

**1 关掉 thinking。** 在 `pipeline/config.py` 的 `THINKING_BUDGET` 里，转写和解读都设成 0。转写是听写，本来就不需要推理。解读输出的是结构固定的 JSON，字段都是定好的，也不需要。这个设置只对 gemini-2.5 系列生效，回退模型自己决定要不要思考。

**2 去掉转写和解读之间的关卡。** 这一条以前写错了，这里改正。887a9bf 之前转写本来就是 3 段同时跑，解读也是同时跑，并行早就有了。真正改的是中间那道关卡，以前要等 3 段全部转写完，才开始解读第 1 段。现在在 `pipeline/session.py` 里，哪一段转写好了，这一段马上开始解读，不等别的。整场总结只等所有转写完成，不等每一条解读完成。

录音按面试官提问的时间切成一段一段，第 i 个回答是从第 i 个问题说完，到第 i+1 个问题开始，每一段用 ffmpeg 单独切出来。

切成短片段还有一个额外好处，Gemini 在长录音上给的时间戳会漂，开头有静音时尤其明显。短片段的时间戳准，再把偏移量加回去，就回到整场的时间轴上。报告里每条评语能点回录音的某一秒，靠的就是这个。

**3 边做边推。** `/api/session_report/stream` 返回 ndjson，一行一个 JSON。事件顺序是 `stage` 说一共几个回答，`transcribed` 报转写进度，`answer` 每出一条回答的反馈就推一条，`summary` 推整场总结，最后 `done` 带完整报告，出错就推 `error`。前端在面试一结束就打开报告页，哪条先回来就先画哪条。

### 结果

同一份合成的 3 问面试，29.5 秒降到 9 到 15 秒。

这个数是 3 件事一起改之后测的，说不清每一件各占多少。README 以前把它全算在关 thinking 上，这是错的，已经改了。拆开怎么测见第 5 节。

这也是一次测试的范围，不是平均值。Gemini 自己的延迟每次波动很大，赶上高峰会更慢。说数字的时候要带上这句，不然被追问「你测了几次」会很难看。

`tests/test_session_stream.py` 离线检查事件顺序和并行，不打真 API。

### 被追问怎么答

**为什么不用 SSE 或者 WebSocket。** 这个请求要带录音上传，是 multipart 的 POST。浏览器的 EventSource 只能发 GET，用不了。前端本来就用 fetch 读响应流，一行一个 JSON 自己就够用，不用再引一层协议。

**为什么用线程不用 asyncio。** 两个阻塞点，一个是 Gemini SDK 的同步调用，一个是 ffmpeg 子进程。一场面试 3 到 4 个回答，线程数很小。代码注释里写了，如果以后一场面试问题变多，要给线程池加上限。

**连接中途断了怎么办。** 前端会显示报告没拿完并给重试。报告本身在后端是算完就写进 SQLite 的，带 `run_id`，没丢。

**英文怎么说。** The report used to arrive in one 32 to 64 second block. I made three changes at once. Thinking off for both model calls, scoring each answer as soon as its own transcript was ready instead of waiting for all of them, and streaming the report as newline delimited JSON. On one synthetic 3 answer interview that took it from 29.5 seconds to 9 to 15. Because they shipped together, I then measured each one on its own.

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
| 29.5 秒降到 9 到 15 秒 | 3 件事一起改之后，同一份合成的 3 问面试，分不出每件各占多少 | README 的 Report speed 一节 |
| 拆开测试的每一项 | 还没测，等 key，见第 5 节 | `eval/split_timing.csv` |
| 追问决定 45 条的准确率 | 只有关键词基线，89%，标注是开发者自己写的，偏简单 | 第 6 节 |
| 追问决定加到停顿上的时间 | 还没测，等 key | 第 6 节 |
| 单题端到端 25 到 31 秒 | eval 跑两个合成样本 | `eval/report.md` |
| 转写 4 到 10 秒 | 内联音频转写 | README |
| 开场问题 0.9 到 1.3 秒 | gemini-3.8-live，6 次运行 | README |
| 免费层一天约 20 次，一份报告约 7 次 | 配额，不是实测，是文档加推算 | README |

**还没测的。** 真麦克风跑完整一场面试、真实用户、上线以后的延迟、人工评分和模型评分的一致性。README 的 Known limitations 里写了这些，面试被问到要照这个说。

---

## 5 拆开测试，3 件事各自省了多少

### 问题是什么

887a9bf 一次交了 3 件事，关 thinking、去掉关卡、流式推送。29.5 秒到 9 到 15 秒是 3 件一起改之后的数。面试被问「哪一件最有用」，现在答不出来。

### 怎么测

`eval/split_timing.py`。每次只在旧设置上改一件事，旧设置就是 887a9bf 之前的样子，thinking 开着，关卡在。

| 配置 | thinking | 关卡 |
|---|---|---|
| baseline | 开 | 有 |
| thinking | 关 | 有 |
| pipeline | 开 | 去掉 |
| all | 关 | 去掉 |

流式推送不需要单独跑。它不改变活儿要干多久，只改变第一条反馈什么时候出现在页面上。所以每一次运行都记两个时间，整份报告的时间，和第一条回答的反馈出来的时间。没有流式，页面要等整份报告才有东西，第一条反馈的时间就等于整份报告的时间。有流式，就是第一条回答事件的时间。这样「只加流式」的数字直接从 baseline 那几次运行里读出来，省掉一整组调用。

测的对象是同一份合成面试，3 段 fixture 录音中间夹 2 秒面试官说话，每次都一样。一份报告 7 次调用，4 个配置一轮 28 次。免费额度每模型每 key 每天大约 20 次，一轮要分 2 天跑。每次运行都记下实际回答的是哪个模型，回退模型回答的那几次不能和别的比。

### 结果

**还没有。** 这个环境里没有 Gemini key，所以一次真实调用都没跑。测试工具本身用假的延迟跑通了，3 段回答都能切出来，4 个配置都能跑完，表格也能出。假延迟的数字只说明开关起作用，不是测量结果，不能引用。

假延迟跑出来有一点值得先记下来，要等真实数字确认。关卡在的时候，加了流式第一条反馈也不会提前，因为第一条解读要等全部转写完才开始。也就是说流式和去关卡是绑在一起起作用的，单独加流式可能几乎没用。如果真实数字也是这样，「只加流式」那一行会接近 baseline，这本身就是一个能讲的发现。

跑完之后把 `python eval/split_timing.py --summary` 的输出贴到这里。

---

## 6 面试官的追问，为什么挂工具

### 问题是什么

面试官以前每个回答后固定追问一次。回答已经很完整也追问，回答缺两样也只追问一次。现在改成每个回答后判断缺什么，缺什么问什么，不缺就换题，每题最多追问 2 次。

### 为什么不在旁边推送决定

原计划是后台用文本模型做决定，再塞给面试官。先算时间。实测面试官在回答结束后 2.9 到 3.3 秒开口，判断回答结束要等 2.5 秒静音，所以从它判断结束到开口只有 0.4 到 0.8 秒。后台决定要在这段时间里走完浏览器到后端、后端到 Gemini、再回来，再注入会话，而注入的时候面试官很可能已经开始生成了。这条路用现有的实测数字就能判断走不通，所以没有再花时间测，直接改成挂工具。

挂工具以后，面试官每个回答后调用 `decide_next_step`，拿到结果才开口，顺序由协议保证。决定还是后台的文本模型做的，`pipeline/followup.py`。代价是决定用的时间会直接加到候选人听到的停顿上。

### 超时和记录

后端 2 秒超时，浏览器 3 秒超时。超时或者出错就退回老规则，每题固定追问一次。每一次决定都记进 `followup_decisions` 表，记来源是模型、上限、超时还是出错，记用了多少毫秒，不记回答的原文。浏览器那边超时还会发一个 `followup_timeout` 事件。上线后看这张表就知道超时有多频繁。

### 追问顺序

缺的东西按具体例子、本人行动、结果数字的顺序问。一开始写的顺序是本人行动排第一，评测集跑出来发现不对。「我一般会列个清单」这种泛泛的回答，没有具体的事，问「你本人做了什么」或者「数字是多少」都接不上，得先问「举一次具体的」。

### 评测

`eval/followup_cases.jsonl` 45 条，17 条什么都不缺，28 条缺东西。看 3 个数，准确率、多余追问率、漏掉追问率。

关键词基线 `--rules` 的结果是准确率 89%，多余追问 0%，漏掉追问 18%。这个数偏高，原因是回答和关键词规则都是我写的，写回答的时候脑子里就有那些关键词。真实的口语转写会乱得多。所以这个数不说明规则好用，只说明这套评测题太容易。要让它有用，得从真实面试里拿回答来补，而且标注要请别人再看一遍。

模型版 `--model` 还没跑，原因同上，没有 key。跑的时候它会同时打印每次决定的耗时中位数，这个数就是加到停顿上的时间。

**英文怎么说。** A follow-up decision pushed from the side would have had about half a second to arrive before the interviewer started talking, so I made it a tool the interviewer calls and waits on. A text model decides what the answer lacks, a specific example, the candidate's own action, or a number, and the code caps follow-ups at two. If the decision takes longer than two seconds, it falls back to the old one follow-up rule and logs the timeout.

# 简历写法

现在的 2 条、问题在哪、改完的版本、还缺什么。只用实测过的数字，没测过的地方都留了方括号，等 A 和 B 做完再填。

---

## 1 现在这 2 条的问题

**原文第 1 条**
> Led product for a 5-person hackathon team building an AI interview coach, interviewing 5 students who said practice tools gave vague feedback, then testing with 8 classmates and fixing 2 scoring errors where Gemini read dorm noise as mumbling and laughter as nervousness.

**原文第 2 条**
> Rebuilt the design with AI coding tools around a live voice interviewer, cutting the report wait from up to 60 seconds to 9 to 15 seconds in testing by streaming results as each answer finishes and citing a timestamped quote in every comment.

4 个问题。

**一条里塞了 3 件事。** 第 1 条同时在说带队、用户访谈、测试修 bug。招聘的人 6 秒扫一条，3 件事挤在一起等于一件都没看进去。

**团队做的和你做的分不开。** 「Led product for a 5-person hackathon team」之后全是你做的事，但读的人没法判断哪些是你、哪些是队友。音频和摄像头是队友写的，这件事写清楚反而加分，因为显得你说话靠谱。

**有动作没结果。** 「fixing 2 scoring errors」说了改了什么，没说改完怎么样。「interviewing 5 students」说了做了什么，没说这个访谈改变了哪个决定。

**第 2 条有一处数字不严谨。** 「up to 60 seconds」对应的实测是 32 到 64 秒，那是 7 次无头浏览器完整跑下来的范围。而「9 到 15 秒」是另一组测试，一份合成的 3 问面试，改之前同一组是 29.5 秒。两个数字来自两套测法，放在一句话里对比，被追问「这两个数是同一个场景吗」会答不上来。要么都用合成那一组，29.5 秒到 9 到 15 秒，要么写清楚是两次不同的测试。

---

## 2 改完的版本，4 条

写成 4 条是因为你的定位是 full stack，用户研究、产品决策、自己把整个应用做出来、评测，这 4 件事各占一条才看得出跨度。简历位置不够就用下面第 3 节的压缩版。

**第 1 条，用户研究变成产品决策**
> Interviewed 5 students about interview practice tools and found one shared complaint, feedback they could not check. Turned it into the product's core rule, every comment must cite a timestamp and the candidate's exact words, and enforced it in code by dropping any comment whose quote is not in the transcript.

为什么这样写。访谈本身不是成果，访谈改变了什么才是。这条的结果是一条能落到代码里的规则，而且这条规则现在真的在 `pipeline/interpret.py` 里跑。

**第 2 条，团队那部分，分工写清楚**
> Led product on a 5-person hackathon team, owning the interface, the front to back integration and the docs while teammates built audio and camera capture. Ran tests with 8 classmates that surfaced 2 scoring errors, Gemini reading dorm noise as mumbling and laughter as nervousness, and fixed both by measuring background noise in code and filtering emotion words out of the model output.

为什么这样写。先说你负责什么，再说队友负责什么，然后测试的结果带到修复方式。「filtering emotion words out of the model output」比「fixing 2 scoring errors」具体，而且这是个有观点的决定，模型不该猜情绪。

**第 3 条，你自己重建整个应用**
> Rebuilt the entire app on my own with AI coding tools, a Gemini Live voice interviewer, a Flask scoring pipeline and a streamed React report. Cut the report wait from 29.5 seconds to 9 to 15 seconds on the same test interview by turning model thinking off, scoring each answer on its own thread, and streaming each result as it finished.

为什么这样写。「Rebuilt the design」听起来像改界面，实际你重建的是整个应用,前端后端都在内，所以写 entire app 并把三块列出来。数字换成同一组测试的 29.5 秒到 9 到 15 秒，这样经得起追问。

**第 4 条，等 A 和 B 做完再填**
> Shipped at [链接]. [N] students ran [M] practice interviews in [几周], and [一个结果数字].

这条现在还写不了。第 4 节说了要补什么。

---

## 3 压缩版，只能放 2 条的时候

> Led product on a 5-person hackathon team building an AI interview coach, owning the interface, the integration and the docs. Interviewed 5 students who could not check the feedback their practice tools gave, turned that into a rule that every comment cites a timestamp and the candidate's exact words, and ran tests with 8 classmates that caught 2 scoring errors where Gemini read dorm noise as mumbling and laughter as nervousness.

> Rebuilt the entire app on my own with AI coding tools, a Gemini Live voice interviewer, a Flask scoring pipeline and a streamed React report. Cut the report wait from 29.5 seconds to 9 to 15 seconds on the same test interview, and shipped it at [链接] where [N] students ran [M] practice interviews.

---

## 4 还缺什么

**最大的缺口是真实用户数和上线链接。** 现在最硬的证据是 8 个同学的测试，而那是黑客松期间的内部测试，不是真实使用。招聘方调研的结论是光有 demo 不够。这个缺口只有 A 和 B 做完才补得上。

A 做完能填的，一份真实麦克风跑出来的报告，可以换掉 README 里的模拟截图。这件事本身不进简历，但面试给人看 demo 的时候，模拟数据和真实数据的区别一眼就能看出来。

B 做完能填的，第 4 条的 3 个方括号，上线链接、用过的学生人数、一个结果数字。

**结果数字选哪一个。** 建议从这 3 个里挑，都是能从 `data/maestro.db` 直接查出来的。

第 1 个，完成率，开始面试的人里有多少把面试做完并拿到报告。这个最能说明产品可用。

第 2 个，回头率，有多少人练了不止 1 次。这个最能说明有用。

第 3 个，做完第 2 次的人里，报告指出的那条问题有没有改掉，比如填充词变少。这个最能说明有效，但要一个人至少练 2 次才算得出来，样本可能不够。

这个要你拍板选哪个，因为它决定上线以后要埋什么、要盯几周。

---

## 5 面试里能说但不写进简历的

这些是追问时的弹药，写进简历会显得啰嗦。

黑客松期间仓库 5 个作者，你有 28 个提交，集中在界面、前后端联调、文档。

10 月你用 AI 编程工具把整个应用重建了一遍，分支是 product-polish，PR 已经合并。

摄像头只在浏览器里算，出去的只有数字。这是隐私决定，不是技术限制。

免费层一天大约 20 次请求一份报告用掉 7 次，所以做了 key 轮换和模型回退。细节在 `docs/tech-notes.md`。

模型不猜情绪，「nervous」这类词在代码里被过滤掉。这是从 8 人测试里那 2 个错误直接来的。

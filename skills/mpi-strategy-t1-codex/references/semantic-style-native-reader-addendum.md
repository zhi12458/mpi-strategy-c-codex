> Integration revision: `semantic-style-native-readers-1` (2026-09-10),
> an editorial addendum to the 1.2.0 quality chain, not a new runtime release.
> The reviewer's guidance below is adopted for the applicable genres. Read it
> before drafting or editing, then execute its closing checks after the core
> workflow. Its suggested routing is implemented in the package entry points.
> It does not authorize a translation run, external transmission, installation,
> or changes to project terminology by itself.

## Integration with the existing workflow

- At intake, before English drafting or editing, retain a source-hash-bound
  `style-and-voice.md`: genre, audience, rhetorical functions, formality,
  oral character, emotional temperature, terminology density, argument rhythm,
  corresponding English register, and any section-level register shifts.
- Use the existing source analysis, segmentation and source-only post-edit map;
  do not create a second competing Chinese authority or repeat certified stages.
  Semantic sentence boundaries do not prescribe English sentence boundaries;
  preserve canonical source/target physical-line and paragraph alignment.
- Reader A is the general nonfiction reader; reader B understands basic
  Buddhism and contemporary Dharma prose without adopting an academic voice.
  Supply only the whole English manuscript and a minimal English genre,
  audience and register brief in the prompt. Hash that prompt. Do not supply
  the source-bound style profile, Chinese, terminology, or editing history.
- Group initial findings as shared, general-reader-only, and Dharma-reader-only
  in the adjudication record, keeping each original finding ID and disposition.
  Agreement sets inspection priority, never permission to change meaning.
- Preserve the existing four-field commissioner proposals and exact-hash
  decisions for material edits. An accepted rule or example in this addendum
  is not advance approval of an individual manuscript edit or term choice.
- Retain `read-aloud-check.md`, bound to the final target hash, recording the
  checked scope (whole document or all high-density passages), locations,
  pauses, stress, referents, logical hierarchy and resolution of problems.
  A model read-through is not evidence that audio or a human oral check occurred;
  record the actual method. Never use word counts or one-breath completion as
  a pass/fail threshold. Recheck Chinese after any naturalization.
- Retain a source/target-hash-bound `publication-checklist.md` with fact and
  quotation checks, source locations, verification status and responsible
  editor. Record no identified items explicitly. Preserve the author's claims
  in translation; unresolved publication checks remain visible for the named
  Dharma reviewer and publication editor, not silently marked verified.
- After approved edits, rerun the full Chinese recheck, bidirectional semantic
  regression and both isolated final readers on the final target hash. Keep
  these internal artifacts outside the clean bilingual Word deliverable and
  index their paths and hashes in the delivery manifest.

These editorial records require substantive operator review; the existing
package validator verifies policy and file integrity, not their semantic truth.
Historical runtime, review and human-approval receipts are not refreshed by this
revision. A draft still requires every existing gate; publication additionally
requires the named Dharma reviewer and publication editor's approval.

---

# T1-Codex 技能包增补说明：中文语义、作者文体与双母语读者审读

## 一、用途与适用范围

本说明作为现有 T1-Codex 佛教中译英技能包的增补规则使用，不替代原技能包中的术语、义理、盲审、语义回归、文件生成和质量控制流程。

它主要解决一种已经在实际编辑中反复出现的问题：译文在字面上没有明显错误，却仍然带有中文句法和抽象表达的痕迹，不像一篇真正面向英文读者出版的文章。

本增补适用于佛教讲稿、开示、访谈、面向大众的文章和由口述整理而成的出版稿。若原文是学术论文、戒律研究、经论讲记或其他专业文体，必须重新判断其文体，不得机械套用大众讲稿的语气。

建议把本文件放入技能包的 `references/` 目录，并在原 `SKILL.md` 中加入以下路由语句：

> When producing or revising publication-facing Buddhist English, read and execute `references/semantic-style-native-reader-addendum.md` after the core workflow. Its source-authority, material-change, and post-edit semantic-regression rules are mandatory.

## 二、总原则

1. 中文原文始终是唯一的语义依据。中文语义分析稿只是理解和重组工具，不得取代或改写原文。
2. 翻译的单位不是孤立的汉字和词组，而是完整的意思、语用功能、逻辑关系、语气和上下文作用。
3. 英文应当让目标读者感到这是自然形成的英文文章，同时完整保留原文的佛学义理、程度、术语、人称关系、语气、比喻、数字和论证方向。
4. “忠实”不等于保留中文表层结构；“流畅”也不等于压缩、软化或改写原意。每次自然化都必须同时通过中文回查。
5. 对高僧大德的尊重，应体现为义理准确、语气稳重和表达清明，而不是人为增加古雅、神圣、夸饰或权威化措辞。

## 三、翻译前新增：中文文体与作者声音定位

在逐段翻译或编辑前，先为全文建立一份简短的“文体与声音说明”，至少判断：

- 文本属于现场讲稿、口述整理稿、访谈、普及文章、学术论述还是经论讲记；
- 预期读者是普通公众、初学佛教者、已有佛学基础者还是专业研究者；
- 作者的语气是讲解、劝导、辨析、批评、反问、抒情还是学术论证；
- 文章的正式程度、口语程度、情感温度、术语密度和论证节奏；
- 英文应采用的对应文体和朗读感。

这一步必须在起草英文之前完成，并在全文编辑过程中保持一致。如果文章内部体裁发生变化，例如由开场讲话转入义理辨析，再进入结语劝勉，英文语域可以随之调整，但作者的整体声音不能漂移。

## 四、济群法师大众弘法讲稿的文体定位

### 1. 基本定位

济群法师的大众讲稿宜定位为：**当代、清明、平实而有义理深度的佛法开示**。

他的表达通常从现实人生、社会现象或听众的实际疑问切入，再逐层界定概念、辨析关系、说明因果，最后回到生命认识和修行实践。语言面向大众，但思想结构严谨；语气亲切、直接、沉着，有时使用反问和生活比喻，却不轻佻、不煽情，也不刻意学院化。

英文的目标文体应是：**适合出版、也适合讲述的 contemporary Dharma prose**。普通英文读者应能顺畅理解；有一定佛教基础的英文读者应能感到术语、义理和法师身份都得到尊重。

### 2. 应保留的声音特征

- 从大家熟悉的现实经验出发，而不是一开始就进入高度抽象的理论语言；
- 常以问题带动思考，并通过 “why,” “what, then,” “in fact,” “in other words,” “so” 等自然英文关系推进论述；
- 由现象进入人心，由人心进入佛法原理，再由原理回到实践；
- 善于用日常比喻解释佛理，比喻应在英文中仍然形成清楚、可想象的画面；
- 适度使用 we，把讲者与听众放在共同观察和修学的位置上，但不得改变原文的人称关系；
- 对问题的判断可以明确有力，但不得擅自替法师软化或强化程度；
- 佛学概念必须准确，同时尽可能通过句法和上下文让非专业读者理解，而不是用额外解释替换原义。

### 3. 应避免的错误定位

- 不要把大众开示译成大学论文或宗教学研究报告；
- 不要因作者是高僧而使用仿古、圣经式或过度庄严的英语；
- 不要把开示改写成励志演讲、自助读物或营销文案；
- 不要用大量抽象名词、被动结构和名词化表达制造“正式感”；
- 不要为了显得通俗而使用俚语、网络语言或过度随意的口吻；
- 不要把法师清楚、循序渐进的重复全部删掉，也不要保留中文中在英文里已经变成累赘的机械重复。应判断每次重复是在推进、强调，还是仅由中文句式造成。

## 五、新增步骤：中文语义分析与语意划分

英文编辑之前，先以中文原文为唯一依据，逐段梳理语义结构。此步骤不重新创作中文，也不改变原文观点。

每段至少检查：

1. **语义主干**：这段主要在说明什么，核心判断是什么；
2. **逻辑关系**：因果、条件、转折、递进、并列、对照、承接、解释和总结分别在哪里；
3. **主语与指代**：省略的主语是谁，“这、其、它、由此、如此”等各指什么；
4. **范围与程度**：否定、限定、频率、可能性、必然性、时间和因果范围是否清楚；
5. **语气与功能**：是在提问、反问、判断、劝导、举例、解释还是总结；
6. **术语与普通词义**：某个词在本段是佛教术语、文化概念，还是普通语用表达；
7. **比喻结构**：本体、喻体和比较关系是否完整；
8. **省略信息**：只补出中文上下文已经包含、而英文语法必须明示的成分，不得增加新命题。

当中文省略主语时，可以在语义分析稿中补明主语。语境确实包含讲者与听众共同参与时，可以使用“我们”帮助理解；但“我们”进入英文前，必须再次确认它没有改变原文的人称范围、责任主体或论断强度。

建议的内部工作格式为：

```text
中文原文：
……

中文语意划分稿：
……

划分说明：
补明了哪些主语；确认了哪些因果、对照、递进或承接关系；有哪些范围和程度必须保护。
```

中文语意划分可以调整分析稿中的句界，以显出真实的意思层次，但不得自动成为最终英文的句子或段落划分。英文仍应按照英语自身的逻辑和节奏重新构建。

## 六、英文起草与编辑：先重建意思，再组织英文

起草每段英文时，依次确认：

1. 英文是否完整表达中文语义分析中确认的全部命题和关系；
2. 英文读者是否能立即看出谁在做什么、为什么、与上一句是什么关系；
3. 是否把中文常用的抽象词组机械换成了英文抽象名词；
4. 是否存在无生命抽象名词承担不自然动作的情况；
5. 是否有名词堆积、支撑动词、重复介词、含混代词或中文式平行结构；
6. 是否为了顺口而删掉条件、程度、佛学区分或作者判断；
7. 是否可以用更常见、更具体的英文动词表达同一意思；
8. 整段朗读时，重音、停顿、推进和收束是否自然。

不要先逐词搭出一个英文骨架，再局部润色。应先理解完整意思，再用英语自然生成这个意思，最后逐项回查中文。

## 七、句子长度规则：以结构清楚为准，不设长短指标

不得把译文限定为短句或中等长度，也不得以句子字数作为质量标准。

句子长度应由以下因素共同决定：

- 一个意思是否需要在同一句中保持完整；
- 因果、条件、对照或递进关系放在一起是否更清楚；
- 主语和谓语之间是否被过多成分隔开；
- 从句层级是否容易辨认；
- 并列项是否真正平行；
- 朗读时是否有自然停顿和足够的呼吸空间；
- 拆开后是否会变成断裂、幼稚或电报式的短句；
- 合并后是否会让读者忘记句首、误认修饰范围或失去论证方向。

长句只要逻辑层级清楚、修饰关系明确、读起来顺畅，就可以保留。短句只在强调、转折、提问、收束或解除结构负担时使用。一个段落应允许长短句自然变化，形成讲稿应有的节奏。

必须执行朗读检查。判断标准不是“能不能一口气念完”，而是听者是否能沿着句子的重音和逻辑自然跟上。

## 八、新增步骤：两类彼此隔离的英文母语读者

候选英文完成并通过中文准确性复核后，交给两类彼此隔离的读者审读：

### 读者 A：一般英文读者／非虚构编辑

关注：

- 是否像自然英文，而不是翻译稿；
- 普通读者能否一次读懂；
- 搭配、主语、代词、逻辑连接和段落推进是否清楚；
- 是否抽象、笨重、重复、书面腔过强或不便朗读；
- 比喻在英文中是否仍然成立；
- 句子节奏是否过碎或过载。

### 读者 B：有一定佛教基础的英文读者

此读者应熟悉基本佛教概念和当代英文佛法开示，但不以学院派佛教学者的语气取代普通读者视角。

关注：

- 佛教术语和常见搭配是否自然；
- 义理层次是否清楚，有无因英语顺滑而造成的概念滑移；
- 法师的教师声音、慈悲、庄重和直接程度是否合适；
- 术语对有基础的佛教读者是否可信，同时是否给普通读者留下足够的上下文；
- 是否出现宗派化、学术化、基督教化或新时代灵性化的无依据表达。

### 隔离要求

两位读者只看完整英文稿，以及必要的体裁、目标读者和语域说明。不得向他们提供中文原文、中文语义分析稿、术语表、其他译文、前序意见或另一位读者的反馈。

他们的任务是以英文读者身份发现问题并提出最小修改建议，不负责判断中文忠实度，也不直接修改最终文件。

## 九、两类读者意见的汇总与裁决

将反馈分成三组：

1. 两位读者共同指出的问题；
2. 只有一般英文读者指出的问题；
3. 只有佛教基础读者指出的问题。

共同意见优先检查，但不能因为两人都觉得顺口就自动接受。每条建议必须回到中文原文、语义分析、术语决定和作者文体中核验。

明显的语法、搭配、代词、重复和标点问题，可以在确认不改变意思后直接修改。

如果修改涉及以下任一事项，不得直接写入最终稿：

- 佛学义理或术语；
- 意义、程度、时态、可能性或因果强弱；
- 作者语气和高僧身份的呈现；
- 比喻、数字、引文或典故；
- 人称关系；
- 增加、删除或压缩信息；
- 句子合并、拆分或段落结构改变；
- 为普通读者增加解释；
- 将文化或政治概念改为功能性意译。

这些项目必须先提交人工决定，格式为：

```text
现有英文：
……

建议英文：
……

修改理由：
……

对原文忠实度可能产生的影响：
……
```

人工决定后，记录决定并对修改后的全文再次做中文语义回归，不能只检查改动句。

## 十、从《佛教的道德观》编辑中提炼的具体经验

### 1. 翻译语用功能，不机械保留词面

中文“结缘”在法师的开场白中可能只是亲切地与听众见面、分享佛法，不一定需要显性译成 *make a Dharma connection*。应先判断该词在语境中的轻重，再选择自然的英文开场表达。文化词不能因为“有文化含义”就一律重译。

### 2. 普通中文表达应优先使用普通英文

“负面新闻层出不穷”在大众讲稿中首先表达“坏消息很多、不断出现”，不应自动升级为抽象新闻评论语。英文应让听众立即明白，再根据上下文补足严重性和频率。

### 3. 不要逐字移植中文抽象搭配

常见问题包括：

- *follow morality* 应根据语境改为 *live morally*、*uphold moral principles* 等；
- *strengthen moral development*、*trials and shocks*、*release positive forces* 等虽然可以猜懂，却不像自然英文；
- *the laws governing the development of life* 这类多层抽象结构，通常可以改用清楚的动词结构，例如说明生命“如何展开”或因果“如何运作”。

修改时必须译出原意，不能只做同义词替换。

### 4. 抽象名词不能被迫承担不自然的动作

如果英文出现“morality operates”“conduct loses order”“life enjoys well-being”等句子，要检查中文真正的施事者和关系。很多问题不是词汇错误，而是中文省略主语后被机械投射到英文造成的。

### 5. 逻辑连接词必须按真实关系选择

中文形式上的“如果说……那么……”有时表达对照而非真实条件，英文可能需要 *whereas*，不能一律使用 *if*。同样，“另一方面”可能是视角转换，也可能是直接转折，应按段落关系选择 *from another perspective*、*on the other hand* 或不用显性连接词。

### 6. 英文必须补清主语和代词，但不能改变责任主体

中文连续省略主语时，英文应补出 people、we、the teaching、the practice、the moral system 等真正主体。含混的 he、it、they 即使语法正确，也会让读者暂时误判。必要时重复名词比使用含混代词更自然。

### 7. “我们”用于共同思考，不用于擅自扩大原文

济群法师的讲稿常邀请听众共同观察人心和社会，适当使用 we 能保留现场感。但原文若明确谈“人们”“修行者”“佛弟子”或某一群体，不得为了亲切一律改成 we。

### 8. 文化概念可作功能性自然化，但必须人工核准

例如“文化自信”在特定语境中可能自然表达为对自身文化传统重新建立认同或自豪，而不是机械保留 *cultural confidence*。这类处理触及政治文化概念的表达方式，必须说明选择和忠实度影响，不能把一次项目决定固化为所有文章的唯一译法。

### 9. 佛教术语要锁定，周边句法要自然

术语本身不能凭英文习惯随意更换，但可以通过自然句法让它容易理解。例如本项目把“善”的核心术语锁定为 *wholesome*；“大沙门”按人工决定使用 *Great Śramaṇa*。这些是项目级决定，不应脱离语境变成普遍术语表。

“安隐”等词也应依据具体引文、论典和上下文决定是 *settled*、*peaceful and secure* 还是其他表达，不能因为某次项目采用 *settled* 就覆盖所有经典语境。

### 10. 不要无依据增加“系统”等现代技术词

“共业”在原文没有“系统”时，不要自动译成 *a system of collective karma*。可直接表达 *collective karma*，或根据句法说明它所形成的共同处境。现代系统语言容易使佛法概念变得机械化。

### 11. “正能量”要译出实际作用

不要敷衍地使用 *a measure of positive energy*。应判断它在本段指积极影响、善的力量、正向心理品质，还是鼓励他人行善的示范作用，再选用 *a positive influence*、*positive qualities* 等符合语境的表达。

### 12. 中文成语和固定说法应保留作用，不强留形状

“吾道不孤”重点可能是知道自己并非独行，从而获得坚持的勇气；“见利忘义”重点可能是为利益放弃正义。若逐字译法在英文中需要读者先解码，就应改用自然表达，同时保留其判断和力度。

### 13. 比喻必须在英文中仍能运作

不能只保留比喻中的名词。要检查英文里的动作和画面是否合理，例如溪流如何汇聚、唇齿如何相依。若英文比喻的物理关系不成立，应在不改变本体和喻体的前提下调整动词；若需要换喻或删喻，必须交由人工决定。

### 14. 译文要适合朗读，但不能因朗读而过度切碎

本项目早期有些句子过长、层级过多，也有后续编辑把复杂意思拆得太碎的风险。正确做法是按语义关系重新组织：需要同句呈现的因果或对照保留在一起；发生主题转换、主语漂移或修饰范围含混时再拆句。

### 15. 标题、目录和正文标题必须单独核对

标题不仅要自然，还要准确表达中文的中心词、修饰范围和并列关系。目录与正文中重复出现的标题必须完全一致；修改正文标题时不能漏改目录，也不能误把新增稿写进目录。

### 16. 不替作者做事实修正，但出版前要标示核查项

涉及历史、社会统计、其他宗教、政治文化和现实事件的断言，翻译阶段应忠实呈现，不得擅自改正。出版流程应另设事实核查清单，核查发现的问题交由作者、编辑或项目负责人决定。

## 十一、出版级最终检查

在形成候选终稿后，至少执行以下检查：

1. 全文逐段回查中文原文，确认无遗漏、增译、弱化、强化和逻辑关系漂移；
2. 检查术语、经名、人名、专名、数字、引文和重复标题的一致性；
3. 检查两类英文读者提出的问题是否均有明确处理结果；
4. 检查所有实质修改是否已经获得人工决定；
5. 以普通英文读者身份连续通读，检查文章整体声音和段落推进；
6. 以佛教基础读者身份连续通读，检查义理、术语和法师语气；
7. 朗读全文或至少朗读高密度段落，检查停顿、重音、指代和句法负担；
8. 单独审读标题、目录、开场、段落首句、转折句和结尾；
9. 建立出版前事实核查与引文核查清单；
10. 最终文件再次核对段落顺序、样式、字体、分页、中文残留和版本一致性。

只有英文自然度复核、中文语义回归、佛学术语复核和文件质量检查全部通过，才可称为“AI-reviewed draft”。是否达到正式出版状态，仍需由具名的佛教专业人工审校者和出版编辑确认。

## 十二、给执行者的简明指令

在使用现有 T1-Codex 技能包处理佛教中译英任务时，请额外执行以下要求：

> 翻译前先判断中文体裁、作者声音、目标读者和对应英文文体。以中文原文为唯一语义依据，逐段完成中文语义分析，补明省略主语，理清因果、条件、转折、递进、并列、对照和承接关系，但不得改写原意。英文应按完整意思重新构建，不保留不自然的中文表层结构。句子不设长短限制，以逻辑清楚、关系明确、自然流畅和适合朗读为标准；长句只要易读即可保留，也不得把复杂论述机械切成短句。候选英文完成后，分别交给彼此隔离的一般英文读者和有一定佛教基础的英文读者，只提供英文稿及体裁说明。汇总反馈后逐条回查中文。语法、搭配、代词、重复和标点等不改变意义的问题可以直接修正；涉及义理、程度、术语、作者语气、比喻、数字、人称、增删信息或句段结构的修改，必须先列出现有英文、建议英文、理由和忠实度影响，由人工决定。济群法师的大众弘法讲稿应译成当代、清明、平实而有义理深度的英文佛法开示：面向普通读者，保持法师的沉着、亲切、直接和循序渐进，不学院化、不仿古、不轻佻，也不改写成励志或自助文体。所有英文自然化修改完成后，必须再次执行全文中文语义回归和英文隔离复审。

## Verb-led English（动词主导的英文）— `verb-led-english-1`

本规则合并至较新的 1.2.0，不降低版本。旧版第 13／14 阶段对应本机第
14／15 阶段；只细化既有 concision 角色，不新增轮次或模型角色。
适用于本工作流的起草与编辑；体裁和准确性优先，不把义理论述强改成行动叙事。

### 中文语义分析与英文起草

- Identify whether the semantic center is an action/process, state, relation,
  definition, or evaluation; identify who acts, changes, experiences, or is
  affected. Record which agency, causality, intention, or degree must not be
  added. Apply these checks in the existing source analysis, segmentation, and
  source-only post-edit map, without creating a new review round.

- For Chinese expressing action, process, change, effect, or practice, normally
  put the central action in a clear English finite verb. Prefer a personal or
  concrete subject supported by the source or context; do not let abstract
  framing carry the main meaning. Never add agency or shift emphasis to obtain
  a verb-led sentence. Accuracy always takes priority.

### Independent action-verb, concision, and naturalness pass

- Inspect the main verb clause by clause across the complete manuscript. Flag
  actions buried in nouns; nominalization, support verbs and abstract carrier
  phrases; empty openings and unnecessary passives; abstract subjects assigned
  unnatural actions; and long noun strings whose semantic center is an action.
- Rewrite only while preserving agent, patient, causality, degree, aspect, logic,
  and emphasis. Do not invent a subject, intention, responsibility, cause, or
  sequence. Retain noun structures, passives, existentials, and copular clauses
  when they accurately express doctrine, states, definitions, or discourse focus.
  No active-voice ratio, verb-count target, or deletion quota is permitted.
- For every execution, retain `verb-led-style-review.jsonl` as specified in the
  addendum, including flagged sentences deliberately retained. In the existing
  editing record, bind the checked draft SHA-256, whole-document completion,
  and issue count. An empty JSONL requires explicit “已完成，零问题” (completed,
  zero issues); absence is not completion. Material edits retain the existing
  commissioner decision requirement.

### 专项问题记录

每次执行都创建 `verb-led-style-review.jsonl`，只记录标出的问题（包括最终决定
保留原句的情况），不是逐句打勾清单。每行一个 JSON 对象，字段为：

- `target_line`: 检查稿中从 1 开始的物理行号；同一行可有多个问题。
- `before`: 检查稿的原英文分句或句子。
- `after`: 实际采纳的英文；决定保留或待人工决定未应用时等于 `before`。
- `issue`: 问题及处理理由，包括保留理由或未决人工选择。
- `source_supported_actor`: 中文或上下文支持的施事及来源定位；无明确施事时
  明记未明示／不适用，不为填字段而虚构主体。
- `protected_constraints_checked`: 实际核验的施受关系、因果、意图／责任、程度、
  可能性、频率、条件、时间／体貌、顺序、逻辑／范围、强调重点与佛学概念及结果。
- `material_change`: 布尔值，标示该项拟议修改是否实质性；未应用不等于非实质。

在既有编辑记录中写明 `checked_target_sha256`（检查前的精确稿件 SHA-256）、
`whole_document_check_completed`、`issue_count`，并索引本 JSONL 的路径与 SHA-256。
保留该检查稿，使行号和 before 可追溯。零问题仍保留空 JSONL，并明确记录
“已完成，零问题”；检查未完成不得写此状态。再次执行保留各次稿件与记录，
不得以新记录覆盖旧证据。实质修改沿用既有人工选项、忠实度影响和决定记录；
此专项记录不代替人工决定，不授权应用尚未批准的修改。

### 语义回归与隔离读者

- Explicitly test whether verb-led revision introduces an unsupported subject,
  stronger intention or responsibility, stronger causality, changed agent/patient
  relations, lost possibility/frequency/conditions, or changed time, aspect,
  sequence, scope, or Buddhist concepts. Apply the same checks to the mandatory
  full-document post-reader regression; retain the complete Chinese recheck
  and independent bilingual semantic regression, not only changed-line checks.

Reader A checks whether actions are buried in nouns or abstract framing,
whether who does what is clear, and whether direct verbs would improve the
English. Reader B flags possible Buddhist conceptual shifts, conditions phrased
as causes, or states and doctrinal relations phrased as intentional actions.
Both readers see English only. Reader B flags suspicions, not Chinese-fidelity
verdicts: only source-based Chinese verification and bilingual semantic
regression determine whether the English departs from the Chinese.

保留全文中文回查、独立双语回归及英文审读后再次全文回归的要求。
包校验只证明规则声明与文件完整性，不证明真实译稿质量或运行就绪。

## 参考依据

济群法师公开资料显示，其弘法内容同时覆盖人生佛教、社会与道德、修学引导、佛学研究、交流答疑和戒律等不同类型，因此每篇文章仍须先判断具体体裁，不能用单一文体覆盖全部著作：

- 济群法师主页：https://www.masterjiqun.com/
- 《解锁人生从学佛开始》：https://jiqun.com/index.php?ac=show&app=@article&id=82
- 《人生佛教的思考》：https://jiqun.com/index.php?ac=show&app=@article&id=585
- 《人工智能时代，人类何去何从》：https://www.jiqun.com/index.php?ac=show&app=@article&id=97
- 《观自在、有为法及其他》：https://www.masterjiqun.com/index.php?ac=show&app=@article&id=78
- 《佛法与人生的三个思考》：https://www.jiqun.com/index.php?ac=show&app=@article&id=209

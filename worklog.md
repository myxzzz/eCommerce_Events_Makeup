# 工作记录

> 按日期记录每天的学习、分析工作和临时想法。

---

## 2026-05-24
- 调整了 copilot-instructions.md：去掉了 AI 主动提醒记笔记的行为，改为按需记录
- 新建了本工作记录文件（worklog.md），用于日常工作日志 + 临时笔记

## 2026-05-25
- 完成了 ABC 组的品牌偏好差异分析（排除 Unknown Brand 干扰）。
- 发现核心买单客群（A组）显著偏好 `runail` 等品牌。
- 发现购物车主动移除客群（C组）显著偏好 `masura` 等品牌（其 C 组流失比例比 A 组高出 1.7 个百分点）。
- 临时想法：明天需要重点针对 `masura`（流失代表）和 `runail`（购买代表）这两个品牌，做一个时间维度的交叉分析，看看是否是因为时间段（例如早晚差异）导致了它们截然不同的转化结果。

## 2026-05-26
- 今日计划：交叉验证时间结论——上午11点左右的入购操作更倾向购买，晚上19-20点左右入购的操作更容易流失，就使用 `masura`（流失代表）和 `runail`（购买代表）这两个品牌。如果说上午入购操作的品牌是`runail`多一些就说明用户流失确实与时间有大关系；如果是`masura`在上午的占比也居高不下，或者早晚这两个品牌的占比没有明显差异，那就说明用户流失的根本原因不是”时间倾向”，而是”品牌本身”的特征（比如价格策略、竞品比价）吃掉了转化率。我刚刚在数据库导入了表03_user_behavior_groups.csv（它比起原表新加一列`group_type`,也去重到了20w行吧）

- 新建 `notebooks/05_品牌时间交叉分析.ipynb`，分析设计如下：

  **分析背景与假设**：
  - 之前的时间维度分析发现：A组（购买）高峰在早上6-11点，B/C组（流失）高峰在晚上18-21点
  - 之前的品牌维度分析发现：runail 是购买代表（A组偏好），masura 是流失代表（C组偏好）
  - 疑问：晚上流失率高，是因为**时间本身**导致用户决策变化，还是因为**某些品牌**在晚上被更多高流失倾向用户看到？

  **分析设计**：
  - 以【品牌 × 时间 × 分组】三维交叉统计
  - 核心指标：C组占比 / A组占比（流失风险比）
    - 比值 > 1：C组占比高于A组，该时段该品牌流失风险高
    - 比值 < 1：A组占比高于C组，该时段该品牌购买倾向强
  - 时间段划分：上午（8-11点，最强购买时段）vs 晚上（18-21点，最强流失时段）

  **关键数据发现**：

  | 品牌 | 时段 | A组(购买%) | B组(被动流失%) | C组(主动流失%) | C/A比值 |
  |------|------|-----------|---------------|---------------|---------|
  | masura | 上午 | 17.06 | 40.06 | 42.88 | **2.51** |
  | masura | 晚上 | 13.06 | 42.92 | 44.02 | **3.37** |
  | runail | 上午 | 22.34 | 43.26 | 34.40 | **1.54** |
  | runail | 晚上 | 18.04 | 47.18 | 34.78 | **1.93** |

  **结论（重要）**：
  1. **时间假设部分成立** —— 同一品牌，晚上确实比上午购买率更低、流失率更高（符合时间偏好差异）
  2. **品牌才是根本差异** —— masura 在任何时段C/A比值都远高于 runail：
     - masura 上午C/A = 2.51 > runail 晚上C/A = 1.93
     - 即 masura 即使在最有利的时间段（上午），流失风险仍高于 runail 最不利的时间段（晚上）
  3. **核心结论**：用户流失的根本原因是**品牌本身特征**（价格策略？竞品比价？产品定位？），时间只是加剧了这个差异，而非源头

  **下一步方向**：
  - 深入 masura 品牌：价格区间分布、与其他品牌的竞品关系
  - 量化”品牌本身”对流失的贡献度，看能否剥离出时间因素的独立影响

## 2026-05-27

- 今日计划：对比 `runail`（购买代表，A组偏好）和 `masura`（流失代表，C组偏好）在“价格”和“品类”上的差异，探究到底是什么特征导致了它们转化归宿截然不同。

- 分析设计如下：
  - **分析目的**：分别对比这两个品牌在 A、B、C 组中的价格分布形态（利用直方图展示），观察 `masura` 是否存在容易导致主动流失的价格带。同时加入 `category_id` 和 `category_code` 分析，以防单独看价格找不出原因。
  - **数据源准备**：直接利用清洗去重好的中间表 `data/interim/03_user_behavior_groups.csv`，其中包含了 `brand`, `price`, `category_id`, `category_code`, `group_type`，非常切合需求。
  - **实现路径**：计划用 SQL 快速聚合提取相关品牌的明细，再切到 Python 用直方图可视化。


## 2026-05-27


- **主力价格带（0-10元）**：这是两个品牌最为集中的价格区间。通过双轴柱线结合图发现，在 0-3元、3-6元、6-10元 这三个区间，`masura` 相对 `runail` 的主动流失风险倍数（M/R）分别为 1.8x, 1.9x 和 1.4x。这条风险倍数线趋于平稳。
- **核心结论（同价不同命）**：排除了价格干扰后，同一价格带内 `masura` 被主动移出购物车的概率依然稳稳地是 `runail` 的 1.5倍左右。**实锤了价格高低不是导致用户流失的根本原因，问题依然出在品牌本身的”护城河”上（产品力、评价、平替等）。**
- **高溢价区（10-15元）**：在这个异常高价段，`masura` 的 C/A 风险比飙升至 6.1！虽然样本量很小（仅 111 个商品），但也说明该品牌在定位上极其缺乏溢价能力，一旦卖贵，消费者绝对不买单。

## 2026-05-31

- **项目收尾**：创建了 `notebooks/07_项目总结与业务建议.ipynb`，将 6 个分析 notebook 的核心结论串成完整的故事线。
  - 分析路线图：漏斗发现流失 → 排除价格 → 锁定品牌 → 时间交叉验证 → 控制价格再验证
  - 新增两张可视化：品牌 ABC 堆叠柱状图 + 品牌流失风险比排行榜（均排除 Unknown Brand）
  - 汇总五大发现 + 四条业务建议 + 局限性声明
  - 最后一个 cell 可以自动导出 `reports/final_report.md`

- **更新 README.md**：
  - 清除了"待决策项"和"分析计划"等过时内容
  - 补充了完整的分析进展（5 个发现）
  - 新增"核心结论"总结表、"业务建议"、"项目结构"、"局限性"板块

- **项目状态**：阶段性完结。后续可在新项目中学习新方法（RFM、cohort、留存分析等）。


## 2026-06-04

- **学习 08 Logistic Regression 建模脚本**
  - 梳理了 sklearn 逻辑回归的完整流程：构造目标变量 `y_purchased` → 选择特征 `X` → One-Hot 编码 → 训练/测试集拆分 → 数值特征标准化 → `LogisticRegression.fit()` 训练 → `predict` / `predict_proba` 预测 → Accuracy、ROC-AUC、混淆矩阵评估 → `coef_` 和 OR 解释特征影响。
  - 明确理解：逻辑回归虽然输出 0/1 分类，但底层先计算“购买概率”；`predict_proba()` 输出概率，`predict()` 按默认阈值 0.5 转成分类结果。
  - 明确理解 `drop_first=True`：One-Hot 编码时少保留一个类别列，不丢信息，还能减少完全共线性；被删除的类别作为参照组，其他类别系数表示“相对参照组”的影响。
  - 理解 Session 特征来源：`08_session_features.csv` 本质上是从原始事件明细按 `user_session` 聚合得到的 Session 画像表，例如 `session_view`、`session_cart`、`session_remove_from_cart`、`session_unique_products`、`session_avg_price`、`session_max_price`；`session_duration_min` 可由同一 session 的 `event_time.max() - event_time.min()` 计算。

- **补充模型结果沉淀**
  - 在 `notebooks/08_logistic_regression建模分析.ipynb` 的系数解释 cell 后新增“保存模型结果到硬盘”cell。
  - 运行该 cell 后会导出：
    - `reports/08_logistic_regression_coef.csv`：完整特征系数、OR（优势比）、方向（促进购买/促进流失）
    - `reports/08_logistic_regression_metrics.csv`：Accuracy、ROC-AUC、混淆矩阵四格、购买/流失 precision、recall、f1
  - 这样以后不用只依赖 notebook 的 print 输出，可以直接用 CSV 复查、筛选和写报告。

- **更新 README.md**
  - 新增第 6 个分析洞察：“逻辑回归建模：Session 行为是最强预测信号”。
  - 补充模型表现：加入 Session 特征后测试集 Accuracy = 0.7986，ROC-AUC = 0.8428，明显优于仅使用商品属性时的 AUC = 0.5707。
  - 更新项目结构：加入 `08_logistic_regression建模分析.ipynb`、`08_session_features.csv`、`08_logistic_regression_results.png`、模型系数和评估摘要 CSV。
  - 更新技术栈：加入 Scikit-learn 和 Logistic Regression。
  - 更新局限性：逻辑回归结果用于相关性解释，不等同于严格因果推断；部分 Session 特征与 C 组定义接近，适合预测流失状态，若要做提前预警，需要只使用预测时点之前的行为特征。

## 2026-06-02

- **新阶段：Logistic Regression 建模分析**
- 使用 `data/interim/03_user_behavior_groups.csv` 作为建模数据源
- 该表说明：原始事件表按 `user_session × product_id` 维度去重聚合，新增 `group_type` 列（A=购买、B=被动流失、C=主动流失），共约 115 万行
- 字段：`user_session, product_id, event_type, price, user_id, brand, category_code, category_id, event_time, group_type`
- 计划用逻辑回归预测加购行为是否转化购买，量化各因素的影响权重



- **项目收尾**：创建了 `notebooks/07_项目总结与业务建议.ipynb`，将 6 个分析 notebook 的核心结论串成完整的故事线。
  - 分析路线图：漏斗发现流失 → 排除价格 → 锁定品牌 → 时间交叉验证 → 控制价格再验证
  - 新增两张可视化：品牌 ABC 堆叠柱状图 + 品牌流失风险比排行榜（均排除 Unknown Brand）
  - 汇总五大发现 + 四条业务建议 + 局限性声明
  - 最后一个 cell 可自动导出 `reports/final_report.md`

- **更新 README.md**：
  - 清除了”待决策项”和”分析计划”等过时内容
  - 补充了完整的分析进展（5 个发现）
  - 新增”核心结论”总结表、”业务建议”、”项目结构”、”局限性”板块

- **项目状态**：阶段性完结。后续可在新项目中学习新方法（RFM、cohort、留存分析等）。

## 2026-06-07

- **重新审视 Logistic Regression 的字段选择问题**
  - 明确当前学习目标不是单纯追求模型分数，而是提升数据分析中的业务理解、字段解释和与 AI 协作的能力。
  - 认识到建模里最难的部分不是 `LogisticRegression()` 本身，而是字段设计：字段是否预测时点前可用、是否接近目标定义、是否有业务含义、字段粒度是否和主表一致。

- **确认 `08_session_features.csv` 的字段口径**
  - 通过抽样对账原始 `data/raw/Dec.csv`，确认 `data/interim/08_session_features.csv` 是从原始事件明细按 `user_session` 聚合得到的整段 Session 画像表，而不是从 `03_user_behavior_groups.csv` 聚合出来的。
  - 字段口径确认：
    - `session_cart`：整段 session 内 `event_type == cart` 的次数
    - `session_remove_from_cart`：整段 session 内 `event_type == remove_from_cart` 的次数
    - `session_view`：整段 session 内 `event_type == view` 的次数
    - `session_duration_min`：同一 session 的 `event_time.max() - event_time.min()`，单位分钟
    - `session_unique_products`：整段 session 出现过的不同 `product_id` 数
    - `session_avg_price`：整段 session 所有事件行的平均 `price`
    - `session_max_price`：整段 session 出现过的最高 `price`
    - `user_total_sessions`：该用户整月不同 `user_session` 数
  - 关键反思：这些字段统计的是“整段 session”，不是“首次加购前”。因此它们更适合作为事后画像/事后识别特征，不适合直接解释为提前预测字段。

- **发现目标泄露风险**
  - 在 `08_logistic_regression建模分析 copy.ipynb` 中删除 `session_remove_from_cart` 和 `session_cart_remove_ratio` 后，模型表现从原先包含全量 session 特征时的 ROC-AUC 约 0.8428 降至 0.6245。
  - 该实验说明原模型的强预测力很大程度来自移除购物车相关字段，而这些字段与 C 组“主动移出购物车”的目标定义非常接近，存在明显目标泄露/透题风险。
  - 当前结论：包含 remove 相关字段的模型适合学习建模流程和做事后识别；如果要做提前预测，需要重新构造预测时点之前的特征。

- **明确下一版特征设计方向**
  - 不推翻旧表，保留 `08_session_features.csv` 作为“整段 session 事后画像”。
  - 后续可新建一张“首次加购前 session 特征表”，预测时点定义为每个 `user_session` 的第一个 `cart` 事件。
  - 第一版候选字段只做简单、可解释的加购前特征：
    - `pre_cart_has_view`
    - `pre_cart_view_count`
    - `pre_cart_unique_products`
    - `pre_cart_unique_brands`
    - `pre_cart_unique_categories`
    - `pre_cart_avg_price`
    - `pre_cart_max_price`
    - `minutes_to_first_cart`
  - 如果某个 session 没有 view 直接 cart，则加购前浏览类字段记为 0，并用 `pre_cart_has_view` 标记；这类 session 不应删除，因为它可能代表目标明确或回购用户。

- **理解字段粒度问题**
  - 当前建模主表粒度是 `user_session × product_id`，即“某个 session 里的某个商品结果”。
  - 新设计的 pre-cart 特征是 `user_session` 级别，合并回主表后，同一个 session 下的多个商品记录会共享同一组 pre-cart 特征。
  - 解释模型时必须区分粒度：
    - `brand`、`price`、`category_id` 是商品级字段，可以解释商品/品牌/价格差异
    - `pre_cart_view_count`、`minutes_to_first_cart` 等是 session 级字段，只能解释用户当次购物状态，不能说成某个商品本身的原因

## 2026-06-09

- **在 notebook 09 中实现首次加购前 Session 特征工程（第三点五步）**
  - 使用 psycopg2 从本地数据库 `makeup_consumer_events.dec` 读取原始事件明细 `df_raw`
  - 完整实现了伪代码中描述的 pre-cart 特征生成流程：
    1. 按 `user_session` 找首次加购时间 `first_cart_time`（Series，index = user_session）
    2. 用 `map` 把 `first_cart_time` 挂回 `df_raw`（比 merge 更轻量，前提是 index 对齐）
    3. 篮选 `event_time < first_cart_time` 的事件，只保留加购前行为
    4. 在加购前事件中只取 `event_type == 'view'`，按 session 聚合生成 8 个特征
    5. 用 `all_cart_sessions` 构建骨架 DataFrame，确保无浏览直接加购的 session 不会丢失（left merge + fillna(0)）
    6. 计算 `minutes_to_first_cart`（session 开始 → 首次加购的分钟数）
  - 特征口径明确：所有聚合字段只基于首次加购前的 view 事件，不含 remove_from_cart 等后续行为
  - 特征表已保存至 `data/interim/09_pre_cart_features.csv`

- **用 pre-cart 特征替换原 session 特征，重新建模**
  - 将 `09_pre_cart_features.csv` 合并回建模主表 `df`（按 `user_session` left merge）
  - 模型特征：`brand`（One-Hot）+ `log_price` + `category_id`（One-Hot）+ 8 个 pre-cart 特征
  - **模型结果（threshold = 0.5）**：
    - Accuracy: 0.5370
    - ROC-AUC: 0.5773（之前无 session 特征时 AUC = 0.5707，原整段 session 特征时 AUC = 0.8428）
    - 流失(0) precision=0.72, recall=0.50；购买(1) precision=0.38, recall=0.60
    - 混淆矩阵：实际流失 42,766 / 41,998，实际购买 16,842 / 25,467
  - **结果解读**：
    - AUC 从 0.5707 微升到 0.5773，说明 pre-cart session 特征比纯商品属性稍好，但提升很小
    - 相比原整段 session 特征的 0.8428 大幅下降，验证了之前的目标泄露判断：原模型的高分主要靠 remove_from_cart 等事后特征"偷看答案"
    - 剔除泄露后，模型的真实预测力有限——加购前的 session 级浏览行为（看了多少商品、浏览了多久）对预测是否购买的帮助不大
    - 这引出一个关键问题：session 级特征粒度太粗，同一个 session 下的多个商品共享同一组特征，无法区分"我认真看了这个商品才加购"和"我随便加购了没看过"

- **明日改进方向 A：加入首次加购商品相关特征（最值得做）**
  - 核心思路：从 session 粒度下沉到"首次加购的那个商品"粒度
  - 围绕首次 cart 的 `product_id` 构造以下特征：
    - `first_cart_product_view_count_before_cart`：该商品在首次加购前被 view 过的次数
    - `first_cart_product_has_view_before_cart`：该商品在加购前是否被看过（0/1）
    - `first_cart_product_last_view_to_cart_min`：该商品最后一次 view → 首次 cart 的时间间隔（分钟）
    - `first_cart_product_brand`：首次加购商品的品牌（可直接从 df_raw 取）
    - `first_cart_product_price`：首次加购商品的价格（可直接从 df_raw 取）
  - 业务含义：用户第一次加购的那个商品，在加购前是否被认真看过？这比 session 总浏览数更贴近目标商品，也更细粒度——同一 session 下不同商品会有不同的 first_cart_product 特征



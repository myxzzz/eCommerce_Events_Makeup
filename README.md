# 电商首次加购后 48 小时结果与品牌运营优先级

## Executive Summary

- **主分析对象是有效 `user_session × product_id` 的首次观测加购，不是“人数”。** 从 353.33 万条 2019 年 12 月事件中，得到 772,119 个能完整观察 48 小时的会话—商品样本。
- **48 小时购买率为 13.56%，未明确处置率为 66.22%，移除率为 20.22%。** B 类占多数，因此不能只在 A/C 子样本中报告“明确结果购买率”40.14%。
- **品牌榜只覆盖 55.99% 的样本。** 原始 `brand` 中大量字面值 `NaN` 已标准化为未知品牌，不再被误当作最大的真实品牌；品牌排序只能代表已知品牌子样本。
- **品牌结论改为“运营排查优先级”，不是因果风险。** `grattol`、`masura`、`ingarden`、`pole`、`bluesky` 等同时具有较高覆盖量和较高移除/购买比，适合优先拆到 SKU 核查，而不能直接断言品牌导致流失。
- **SQL 与 Python 共 25 项正式检查为 0 个错误。** 唯一警告是旧 48 小时 CSV 多出 369 个无效会话样本；旧版被保留为学习轨迹，不再作为正式数据源。

---

## 正式口径

| 项目 | 定义 |
|---|---|
| 主粒度 | 一个有效会话内一个商品的首次观测加购 |
| 主窗口 | 首次观测加购后 48 小时，窗口必须完整 |
| A | 48 小时内出现购买；购买优先 |
| C | 48 小时内无购买，但出现移除 |
| B | 48 小时内既未购买也未移除 |
| 主购买率 | A/(A+B+C) |
| 移除/购买比 | C/A；描述性运营信号，不是概率或因果风险 |
| 时间解释 | 全部按 UTC；业务时区未知，不做早晚时段运营结论 |

完整定义见：

- [项目立项书](docs/project_charter.md)
- [数据字典](docs/data_dictionary.md)
- [指标字典](docs/metric_dictionary.md)
- [成果清单与旧/正式版本说明](docs/artifact_inventory.md)
- [逐项企业化优化记录](docs/optimization_log.md)
- [环境与复现说明](docs/environment_and_reproduction.md)
- [面试项目表达](docs/interview_story.md)
- [14 天综合学习计划](docs/14_day_integrated_learning_plan.md)

## 本轮企业化优化了什么

| 原项目风险 | 正式处理 | 为什么 |
|---|---|---|
| 把 `user_id × product_id` 或其他粒度标成“人数” | 事件、用户、会话、会话—商品漏斗分层 | 防止分子分母和业务对象混乱 |
| 旧 A/B/C 可能不是严格“加购后”结果 | 从首次观测加购重建 48 小时队列 | 消除事件顺序错误 |
| `user_session="NaN"` 被当作同一会话或被 Pandas 静默丢组 | 作为无效会话键排除 | 防止跨用户串联和 SQL/Python漂移 |
| `brand="NaN"` 被当作最大品牌 | 标准化为未知品牌并报告覆盖率 | 防止品牌榜严重失真 |
| 品牌覆盖量只看 A+C | 改为 A+B+C，同时保留明确结果指标 | B 占 66%，不能从业务规模中消失 |
| `C/A risk ratio` 容易被理解为风险概率 | 改名“移除/购买比” | 它只是比值，不是因果或概率 |
| 固定 1.5 被当作行业标准 | 标为可调启发式筛选线 | 阈值需要未来按成本或历史基线校准 |
| 月末和不同窗口分母变化 | 24/48/72 小时使用同一批 72 小时完整样本 | 避免截断造成伪差异 |
| 缺少跨工具对账 | SQL 明细、Python 重新聚合和 Excel 同源 | 保证交付数字可追溯 |
| 旧模型按行随机切分 | 正式交付不使用模型结论 | 同会话信息泄露且当前预测价值不足 |

## 正式结果与交付物

- 正式只读 SQL：[`sql/formal/`](sql/formal/README.md)
- Python 执行与对账：[`scripts/run_formal_validation.py`](scripts/run_formal_validation.py)
- 正式可执行 Notebook：[`notebooks/11_正式分析与验证.ipynb`](notebooks/11_正式分析与验证.ipynb)
- 数据质量报告：[`reports/data_quality_report.md`](reports/data_quality_report.md)
- 正式交付 QA：[`reports/delivery_qa_report.md`](reports/delivery_qa_report.md)
- 管理层一页报告源：[`reports/management_onepager_source.md`](reports/management_onepager_source.md)
- 可验证管理层报告快照：[`reports/management_report_artifact.json`](reports/management_report_artifact.json)
- 正式图表：[`reports/formal_charts/`](reports/formal_charts/)
- 正式 Excel：[`outputs/formal_delivery/eCommerce_brand_priority_formal.xlsx`](outputs/formal_delivery/eCommerce_brand_priority_formal.xlsx)
- Power BI 两页实施规范：[`reports/power_bi_formal_spec.md`](reports/power_bi_formal_spec.md)
- DAX 度量值：[`reports/power_bi_measures.dax`](reports/power_bi_measures.dax)

`reports/first_brand.pbix` 和旧 Excel/Notebook/图表保留为练习版。当前本机无法发现 Power BI Desktop，因此没有伪造新的 PBIX；正式 CSV、页面设计和 DAX 已准备好。

## 仓库整理结果与导航

这次整理把项目分成三层，避免正式结果、历史练习和本机生成物混在一起：

1. **正式链路**：`docs/`、`sql/formal/`、正式验证脚本、Notebook 11、正式报告、正式 Excel 和 Power BI 规范。面试、复现和业务结论以前述文件为准。
2. **历史探索**：Notebook 01—10、旧 SQL、旧图表、练习 Excel 和第一版 PBIX。它们保留学习轨迹，但不再作为正式口径证据。
3. **本机生成物**：原始数据、中间表、逐样本明细、依赖目录和 QA 预览。这些文件体积大或可重建，由 `.gitignore` 排除，不上传 GitHub。

```text
eCommerce_Events_History/
├── data/                         # 本机数据；原始与中间数据默认不提交
│   ├── raw/                      # Dec.csv 等原始数据
│   ├── interim/                  # 探索/建模中间表
│   └── processed/                # 可重建处理结果
├── docs/                         # 立项、字典、优化记录、复现与学习计划
├── notebooks/
│   ├── 01—10                    # 历史探索与建模练习
│   └── 11_正式分析与验证.ipynb  # 正式、可顺序运行的 Notebook
├── sql/
│   ├── 00—07                    # 历史探索 SQL
│   └── formal/                  # 正式只读 SQL 00—06
├── scripts/                      # SQL执行、Python对账、图表/报告/Notebook与QA
├── reports/
│   ├── data_exports/            # 小型正式汇总和对账证据
│   ├── formal_charts/           # 正式图表
│   ├── data_quality_report.md
│   ├── management_onepager_source.md
│   ├── power_bi_formal_spec.md
│   └── power_bi_measures.dax
├── outputs/formal_delivery/      # 正式 Excel；内部预览和检查快照不提交
├── tools/excel_formal/           # Excel 生成逻辑；node_modules 不提交
├── .env.example                  # 无密码的连接参数示例
├── .gitignore
├── requirements.txt
└── README.md
```

### Git 中保留与忽略的边界

| 类型 | Git 策略 | 原因 |
|---|---|---|
| SQL、Python、Markdown、正式 Notebook | 提交 | 核心逻辑、口径和审计轨迹 |
| 正式 Excel、小型汇总 CSV、正式图表 | 提交 | 便于直接查看结果和跨工具对账 |
| `data/raw/`、`data/interim/`、`data/processed/` | 忽略 | 当前本机数据约 755 MB，可从原始来源或脚本重建 |
| `cohort_detail_48h.csv` | 忽略 | 逐样本明细约 128 MB，超过 GitHub 普通单文件限制 |
| `node_modules/` | 忽略 | 本机依赖超过 7,000 个文件，可重新安装或由运行环境提供 |
| QA 预览、`.inspect.ndjson`、Office 锁文件 | 忽略 | 可重建的内部检查产物，不属于正式交付 |
| `.env`、本机 AI/编辑器配置 | 忽略 | 避免凭据和个人环境进入仓库；只提交 `.env.example` |

正式 Excel 已提交为可直接查看的交付物。`tools/excel_formal/build_excel.mjs` 使用 Codex 提供的电子表格运行时；普通 Python 环境无法直接执行它时，可使用已提交的正式 Excel，或从 `reports/data_exports/` 手工/Power Query 导入汇总数据。

## 复现

本项目在 `data-learning` Conda 环境（Python 3.13.7）中验证通过；`D:\conda-envs\data-learning\python.exe` 是作者本机路径，不是其他机器必须使用的固定路径。数据库密码不得写入仓库；连接参数从 PostgreSQL 本机默认认证或环境变量读取。

```powershell
python -m pip install -r requirements.txt
python scripts\run_formal_validation.py
python scripts\build_formal_artifacts.py
python scripts\build_formal_notebook.py
python -m jupyter nbconvert --execute --to notebook --inplace notebooks\11_正式分析与验证.ipynb
python scripts\run_delivery_qa.py
```

正式 SQL 只读运行，不创建、更新或删除数据库对象。大表聚合在 PostgreSQL 完成，Python 只读取正式导出和必要中间表。

---

## 历史探索记录（旧口径，保留但不作为正式结论）

以下内容记录项目早期的分析思路和学习过程。其中部分数字、时间段结论、品牌因果措辞和模型分数已被正式审计收紧；面试或展示时应以前面的正式口径和文件为准。

## 问题是什么？

这个项目的核心问题是：

> 在电商化妆品场景中，用户已经把商品加入购物车，为什么仍然没有完成购买？

我没有把它简单写成“做一个用户行为分析”，而是把它拆成一个更接近业务的问题：

1. 购物车是不是主要流失环节？
2. 用户不买是不是因为价格太高？
3. 如果不是价格，是不是品牌、时间段或用户行为模式造成差异？
4. 哪些品牌应该被加大流量，哪些品牌应该重点治理？
5. 如果要做提前预警，现有数据能不能预测用户是否会购买？

项目最终希望回答的不是“哪个模型分数最高”，而是“运营应该把力气花在哪里”。

---

## 我怎么验证？

我的验证路线是“先定位问题，再逐步排除解释”。

### 1. 先用漏斗确认问题发生在哪里

先统计 `view`、`cart`、`remove_from_cart`、`purchase` 的行为链路，确认用户不是没有兴趣，而是在加购后大量流失。

![用户行为漏斗](reports/02_user_funnel.png)

从中间表口径看，A/B/C 三类结果样本分别为：

| 分组 | 含义 | 样本量 |
|---|---|---:|
| A | 加购后购买 | 211,633 |
| B | 加购后未购买、也未主动移出购物车 | 518,495 |
| C | 加购后主动移出购物车 | 424,063 |

这个结果把分析方向锁定在“加购后的转化/流失”，而不是泛泛分析全站浏览行为。

### 2. 再看价格，验证“是不是卖贵了”

我对比了 A/B/C 三组的价格分布：

| 分组 | 平均价格 | 中位数价格 |
|---|---:|---:|
| A 购买 | 5.06 | 3.11 |
| B 被动流失 | 5.31 | 3.33 |
| C 主动流失 | 5.34 | 3.81 |

![价格指标对比](reports/03_price_metrics_comparison.png)

三组价格差异存在，但不大，价格分布高度重合。因此我没有把“价格太高”当成主结论，而是把它作为一个被削弱的解释。

### 3. 然后看品牌，寻找稳定差异

价格解释不够强之后，我转向品牌维度，比较购买组和流失组的品牌结构。

![品牌ABC分布](reports/07_brand_abc_stacked_bar.png)

关键发现是：不同品牌在 A 组和 C 组中的占比差异明显。

- `runail` 在 A 组占比 8.54%，在 C 组占比 7.39%，更偏向购买。
- `masura` 在 A 组占比 3.26%，在 C 组占比 5.02%，更偏向主动流失。
- `estel`、`kapous` 等品牌也更偏健康；`bluesky`、`cosmoprofi` 等品牌更偏高风险。

这一步把问题从“用户为什么不买”推进到“哪些品牌在当前口径下更容易出现在主动流失结果中”。

### 4. 用时间交叉验证，避免把时间误判成品牌

前面发现购买高峰更集中在早上，流失高峰更集中在晚上。为了验证品牌结论是不是被时间段干扰，我对 `masura` 和 `runail` 做了品牌 × 小时 × 分组交叉分析。

![时间分布](reports/03_time_point_distribution1.png)

![品牌时间交叉分析](reports/05_brand_time_cross_analysis.png)

关键对比：

| 品牌 | 时段 | A 组占比 | C 组占比 | C/A 风险比 |
|---|---:|---:|---:|---:|
| masura | 上午 8-11 点 | 17.06% | 42.88% | 2.51 |
| masura | 晚上 18-21 点 | 13.06% | 44.02% | 3.37 |
| runail | 上午 8-11 点 | 22.34% | 34.40% | 1.54 |
| runail | 晚上 18-21 点 | 18.04% | 34.78% | 1.93 |

时间确实有影响：同一品牌晚上更容易流失。但 `masura` 在最好时段的风险比 2.51，仍高于 `runail` 在最差时段的 1.93。  
所以我把时间定义为影响因素，但不把它作为品牌差异的唯一解释。

### 5. 控制价格后再看品牌，验证“同价不同命”

为了进一步排除价格干扰，我把 `masura` 和 `runail` 放在同一价格带里比较。

![价格品牌分析](reports/06_price_brand_group_analysis.png)

| 价格带 | masura C/A | runail C/A | 解释 |
|---|---:|---:|---|
| 0-3 | 2.98 | 1.67 | 同低价段，masura 仍更容易流失 |
| 3-6 | 3.72 | 1.96 | masura 风险约为 runail 的 1.9 倍 |
| 6-10 | 2.55 | 1.80 | 风险差距仍存在 |
| 10-15 | 6.10 | 1.49 | masura 高溢价段流失风险明显放大，但样本较小 |

这一步是项目里比较关键的验证：即使价格相近，品牌之间的流失差异依然存在。  
这说明品牌维度值得继续分析，但它背后具体对应产品力、评价、替代品竞争还是用户信任，需要更多商品详情、评价和促销数据才能进一步验证。

### 6. 用 Logistic Regression 做量化验证，并识别目标泄露

我用 Logistic Regression 预测“加购后是否购买”，把 A 组作为购买样本，C 组作为主动流失样本，剔除结果不明确的 B 组。

![逻辑回归结果](reports/08_logistic_regression_results.png)

初版模型加入整段 session 行为特征后：

| 指标 | 数值 |
|---|---:|
| Accuracy | 0.7986 |
| ROC-AUC | 0.8428 |
| 测试样本 | 127,081 |

但复盘字段后发现，`session_remove_from_cart`、`session_cart_remove_ratio` 等字段统计的是整段 session，其中包含了结果发生后的行为。这些字段和 C 组定义高度重叠，存在目标泄露。

所以我做了第二轮验证：

1. 删除明显泄露字段后，AUC 从 0.8428 降到 0.6245。
2. 重新构造“首次加购前”的 pre-cart 特征，只使用第一次 `cart` 事件之前的浏览行为。
3. 使用品牌、价格、品类和 8 个 pre-cart 特征重新建模，ROC-AUC 为 0.5773，只比纯商品属性模型 AUC 0.5707 略高。

这个结果说明：如果目标是提前预警，session 级浏览行为的预测力有限；下一步应把特征粒度下沉到“被加购商品本身”，例如该商品加购前是否被浏览过、浏览到加购间隔多久。

---

## 用了什么数据？

### 原始数据

- 数据来源：Kaggle - Ecommerce Events History in Cosmetics Shop
- 时间范围：2019 年 12 月
- 原始文件：`data/raw/Dec.csv`
- 文件大小：约 415 MB
- 事件类型：`view`、`cart`、`remove_from_cart`、`purchase`
- 核心字段：
  - `event_time`：事件时间
  - `event_type`：行为类型
  - `product_id`：商品 ID
  - `category_id` / `category_code`：品类信息
  - `brand`：品牌
  - `price`：价格
  - `user_id` / `user_session`：用户与会话标识

### 分析中间表

| 文件 | 作用 |
|---|---|
| `data/interim/03_user_behavior_groups.csv` | 主分析表，按 `user_session × product_id` 聚合并标记 A/B/C 分组 |
| `data/interim/03_price_stats.csv` | A/B/C 三组价格统计 |
| `data/interim/03_time_summary_point.csv` | A/B/C 三组小时分布 |
| `data/interim/04_abc_brand_analysis.csv` | 品牌在 A/B/C 三组中的占比 |
| `data/interim/05_brand_time_cross_analysis.csv` | 品牌 × 小时 × 分组交叉验证 |
| `data/interim/06_price_brand_group_analysis.csv` | `masura` 与 `runail` 在不同价格带的风险对比 |
| `data/interim/08_session_features.csv` | 整段 session 行为特征，用于初版建模，存在事后字段 |
| `data/interim/09_pre_cart_features.csv` | 首次加购前 session 特征，用于剔除目标泄露后的复测 |
| `data/interim/10_brand_quadrant_matrix.csv` | 品牌四象限分层结果 |
| `data/interim/11_user_behavior_groups_window_48h.csv` | 以首次真实 `cart` 为起点的 48 小时观察窗口分组表 |
| `data/interim/11_brand_quadrant_matrix_window_48h_fixed_risk_1_5.csv` | 48 小时口径下，使用固定 `C/A >= 1.5` 风险阈值的品牌四象限 |

### A/B/C 分组口径

| 分组 | 业务含义 | 解释 |
|---|---|---|
| A | 购买用户/商品 | 加购后最终购买 |
| B | 被动流失 | 加购后没有购买，但也没有主动移出购物车 |
| C | 主动流失 | 加购后主动 `remove_from_cart` |

其中 A 和 C 是结果最明确的两组，所以建模时主要使用 A/C 做二分类，B 组更多用于描述整体流失结构。

### 48 小时窗口补充口径

复盘后发现，原 `03_user_behavior_groups.csv` 存在时间窗口边界问题：12 月末首次加购样本可能没有完整后续观察期；部分 A/C 结果也可能对应 12 月前已经加购、12 月内才购买或移除的历史购物车行为。

因此新增一版 48 小时固定观察窗口：

| 分组 | 48 小时窗口定义 |
|---|---|
| A | 首次真实 `cart` 后 48 小时内出现 `purchase` |
| C | 48 小时内没有 `purchase`，但出现 `remove_from_cart` |
| B | 48 小时内既没有 `purchase`，也没有 `remove_from_cart` |

过滤条件：只保留 `first_cart_time < 2019-12-30 00:00:00+00` 的样本，保证每条样本都有完整 48 小时观察窗口。若同一窗口内同时出现 remove 和 purchase，按最终成交优先，归为 A。

新口径结果：

| 分组 | 样本量 | 占比 |
|---|---:|---:|
| A | 104,696 | 13.55% |
| B | 511,656 | 66.23% |
| C | 156,137 | 20.21% |

与旧口径相比，B 组占比明显上升，A/C 占比下降。这个结果说明，在首次加购后的短期窗口内，很多用户并不会立即购买或移除；旧口径中的一部分购买/移除结果可能来自更长决策周期或历史购物车状态。

---

## 为什么这么做？

### 1. 因为业务问题需要“排除法”，不是只看相关性

如果只看一张价格图、品牌图或模型结果，很容易得出过早结论。  
所以我采用的是：

1. 用漏斗锁定问题环节。
2. 用价格对比排除最直觉的解释。
3. 用品牌分组寻找更稳定的差异。
4. 用时间交叉验证确认品牌差异不是时间造成的。
5. 用控制价格后的品牌对比确认“同价不同命”。
6. 用建模量化影响，但同时检查字段是否泄露。

这条路线的重点是让结论经得起追问。

### 2. 因为购物车流失是一个运营问题

购物车流失不是单纯预测问题。业务真正关心的是：

- 哪些用户值得挽回？
- 哪些品牌应该给更多曝光？
- 哪些品牌虽然有流量但转化差，需要治理？
- 什么时间点适合提醒？
- 如果模型要上线，预测时点之前到底能看到哪些字段？

所以我没有只停留在模型分数，而是把每个发现翻译成可行动的运营策略。

### 3. 因为“目标泄露”本身就是数据分析能力的体现

初版模型 AUC 很高，但字段里包含移出购物车次数，这相当于在预测“是否流失”时偷看了“是否已经移出购物车”。  
发现并修正这个问题，比保留一个漂亮但不可信的高分更重要。

这也是这个项目可以讲给面试官听的地方：我不仅会跑模型，也会判断模型结果能不能在真实业务中使用。

---

## 发现了什么？

### 发现 1：购物车是主要流失环节

用户不是完全没有兴趣，而是在加购之后没有完成购买。A/B/C 分组中，明确购买样本 211,633，主动移出购物车样本 424,063，主动流失规模明显大于购买规模。

业务解释：加购后的提醒、优惠、商品详情优化和品牌侧运营，可能比单纯拉更多浏览流量更接近问题发生的位置。

### 发现 2：价格不是最主要的流失解释

A 组平均价格 5.06，C 组平均价格 5.34；中位数分别为 3.11 和 3.81。流失组价格略高，但差异不足以解释大规模流失。

业务解释：不能简单把流失归因于“太贵了”，否则容易误用降价策略。更应该继续追查品牌、品类、用户决策过程。

### 发现 3：品牌差异比价格差异更稳定

`runail`、`estel`、`kapous` 等品牌更偏购买；`masura`、`bluesky`、`cosmoprofi` 等品牌更偏主动流失。

业务解释：品牌不是一个普通维度，它可能承载产品定位、价格带、品类结构、用户认知等多种差异。当前数据能证明品牌结果不同，但不能单独证明差异来自产品力或口碑。

### 发现 4：时间影响转化，但不是唯一解释

购买更集中在早上 6-11 点，流失更集中在晚上 18 点到次日 4 点。  
但品牌交叉验证显示，`masura` 在上午的风险仍高于 `runail` 在晚上。

业务解释：时间适合用于设计触达时机，但不能替代品牌和商品维度的进一步拆解。比如 16 点前后可以作为购物车提醒的候选窗口，但是否有效仍需要实验验证。

### 发现 5：控制价格后，品牌差异仍然存在

在 0-3、3-6、6-10 等主力价格带内，`masura` 的 C/A 风险比都高于 `runail`。  
尤其在 10-15 元价格带，`masura` C/A 达到 6.10，说明它在高溢价区更容易被用户放弃。

业务解释：某些品牌在较高价格带的主动流失风险更高，但原因可能包括品牌认知、商品结构、价格带样本量和促销信息缺失等。后续策略上应优先做小规模验证，而不是直接推断为品牌缺乏溢价能力。

### 发现 6：品牌可以分成四类运营

基于品牌体量和流失风险，我把品牌分成四象限：

| 象限 | 代表品牌 | 业务含义 |
|---|---|---|
| 核心健康品牌 | `runail`、`irisk`、`bpw.style` | 高体量、相对低风险，是优先测试增加曝光的候选品牌 |
| 重点治理品牌 | `masura`、`grattol`、`ingarden` | 高体量、高风险，需要加购挽回和详情页治理 |
| 潜力长尾品牌 | `kaaral`、`benovy`、`skinlite` | 低体量、低风险，可小流量测试放量 |
| 问题长尾品牌 | `shik`、`beauty-free`、`ecolab` | 低体量、高风险，优先级最低，可降低推荐权重 |

![品牌四象限矩阵](reports/10_brand_quadrant_matrix.png)

业务解释：这个分层可以作为流量分配、品牌治理和运营优先级排序的候选依据，但正式动作前还需要结合利润、库存、促销、评价和曝光数据。

### 发现 7：48 小时窗口验证后，品牌差异仍存在，但四象限阈值需要固定

新增 48 小时观察窗口后，A/C 规模下降，B 组占比上升。品牌层面，`masura` 的 48 小时 C/A 为 2.3093，仍高于 `runail` 的 1.3548，说明品牌差异没有被时间窗口口径完全解释掉。

但新口径下整体 C/A 风险下降，中位数风险阈值降到 1.268987，导致 `runail`、`irisk` 这类高体量品牌在相对分层中被推到“高风险”。因此补充固定阈值版本：`C/A >= 1.5` 记为高风险。固定阈值下，`runail`、`irisk` 仍属于核心健康品牌，`masura`、`grattol`、`ingarden`、`pole`、`bluesky` 仍属于重点治理品牌。

### 发现 8：模型高分不等于可用，预测时点很关键

初版模型 ROC-AUC 0.8428，但存在目标泄露；剔除泄露并只使用首次加购前行为后，ROC-AUC 只有 0.5773。

业务解释：如果只是做事后复盘，整段 session 特征有解释价值；如果要做提前预警，就只能使用预测时点之前可见的字段。下一步应该构造商品级 pre-cart 特征，而不是继续堆 session 级特征。

---

## 对业务有什么意义？

### 1. 运营策略从“全量促销”转向“品牌分层验证”

如果只知道购物车流失严重，常见动作是全量发券。  
但这个项目说明，不同品牌的流失风险差异很大，更合理的做法是先按品牌分层设计候选策略，再通过小规模实验验证：

- 核心健康品牌：可以测试增加搜索、推荐、首页曝光，观察是否能稳定放大转化。
- 重点治理品牌：可以测试加购后提醒、评价露出、替代品推荐、限时优惠或详情页优化。
- 潜力长尾品牌：可以小流量测试，观察低体量品牌是否具备放量空间。
- 问题长尾品牌：可以降低推荐优先级或减少资源投入，但需要结合利润、库存和战略价值判断。

### 2. 价格策略不应一刀切

价格不是整体流失的最强解释，但部分品牌在较高价格带的风险更高。  
因此更合理的策略不是直接全站降价，而是：

- 对高风险品牌的高价段做单独监控。
- 对 10-15 元高风险价格带测试赠品、组合销售或优惠提示。
- 对相对健康品牌避免盲目降价，先验证曝光和推荐是否能带来增量。

### 3. 时间可以用于触达，但不能替代商品治理

流失高峰集中在晚上，说明提醒时机有优化空间。  
一个候选动作是：在下午 16 点左右识别购物车内仍有商品的活跃用户，在晚间流失高峰前做提醒或优惠触达。

但时间只是触达窗口，不应被解释为流失的唯一原因。真正的优先级仍然应该结合品牌、商品、价格带和用户行为。

### 4. 建模方向从“事后识别”转向“提前预警”

项目后半段最大的收获是明确了预测时点：

- 如果用整段 session 字段，可以识别“谁已经表现出流失迹象”。
- 如果要提前预警，只能使用首次加购之前的行为。
- session 级 pre-cart 特征预测力弱，下一步应该做商品级 pre-cart 特征。

这让后续项目方向更清楚：不是继续追求模型分数，而是重新设计业务可用的特征。

---

## Excel 与 Power BI 交付练习

在完成品牌四象限分析后，我补充了一版 Excel 和 Power BI 交付练习，目标不是重新计算所有指标，而是把已经验证过的分析结果整理成业务方能阅读、筛选和复查的交付物。

### 1. Excel：把分析结果整理成业务可读表

Excel 文件：`reports/eCommerce_brand_quadrant_excel_practice.xlsx`

这一版主要使用 `reports/11_brand_quadrant_matrix_window_48h.csv` 作为品牌汇总数据源，而不是直接导入原始事件明细。原因是原始事件表适合用 SQL/Python 做清洗和聚合，Excel 更适合作为轻量交付层，用来展示口径、补充业务标签、制作透视表和快速给业务方查看结果。

Excel 中重点整理了三类内容：

- 指标口径说明：明确 A/B/C 分组、明确结果购买率、C/A 风险比、品牌体量和分析粒度。
- 品牌明细表：把 `brand_clean`、`ac_purchase_share`、`c_to_a_ratio` 等分析字段改成“品牌”“明确结果购买率”“C/A风险比”等业务可读字段，并补充风险等级和建议动作。
- 品牌透视汇总：按品牌象限和风险等级汇总品牌数、购买样本数、移除样本数、明确结果样本数和风险指标。

这一步的核心收获是：交付给业务方的表不应该只是“代码算出来的字段”，而应该包含清楚的口径、可读字段名、筛选条件、样本量提醒和可执行动作。

### 2. Power BI：区分明细列和动态度量值

Power BI 文件：`reports/first_brand.pbix`

Power BI 第一版直接读取 Excel 中的 `02_品牌明细表`。这里不读取透视表或摘要页，因为 Power BI 的数据源应该是结构化明细表，而不是已经排版过的展示结果。

在 Power BI 中重新建立核心度量值，而不是直接平均 Excel 里的比例字段：

```DAX
总购买样本数 = SUM(brand_summary[购买样本数])
总移除样本数 = SUM(brand_summary[移除样本数])
明确结果样本数 = SUM(brand_summary[明确结果样本数])
明确结果购买率 = DIVIDE([总购买样本数], [明确结果样本数])
C/A风险比 = DIVIDE([总移除样本数], [总购买样本数])
品牌数 = DISTINCTCOUNT(brand_summary[品牌])
```

这里的关键认识是：Excel 表中的 `明确结果购买率` 和 `C/A风险比` 是单个品牌的行级指标；Power BI 看板中的 KPI 卡片和图表需要的是当前筛选条件下的整体指标。比如整体购买率不能用品牌购买率的简单平均，而应该用 `SUM(购买样本数) / SUM(明确结果样本数)`。

因此，Power BI 的价值不是把 Excel 图表搬过去，而是让指标随着切片器动态变化：当筛选品牌象限、风险等级或某一类品牌时，卡片、柱状图和明细表都按同一套度量值重新计算。

### 3. 对口径和交付的认识

这次补充练习让我把“分析口径”和“交付口径”分开理解：

- 分析口径解决的是：一行数据代表什么、样本范围是什么、指标怎么算、边界情况怎么处理。
- 交付口径解决的是：业务方看到什么字段、如何筛选、哪些指标能汇总、哪些比例不能直接平均、样本量不足时要不要提醒。
- Excel 适合做轻量交付、透视汇总和临时业务沟通；Power BI 更适合做可交互看板、切片器筛选和动态 KPI。
- BI 看板里的核心指标应该优先用 Measure 定义，而不是依赖静态列的默认汇总。

这部分不是新的业务结论，而是把同一套分析结果从“我能算出来”推进到“别人能看懂、能筛选、能用于讨论”。

---

## 如果面试讲 10 分钟，可以这样讲

1. **先讲问题**：我研究的是化妆品电商里用户加购后不购买的问题，希望找出流失原因和运营干预点。
2. **讲数据和口径**：数据来自 Kaggle 2019 年 12 月事件日志，我按 `user_session × product_id` 聚合，把加购后的结果分成购买 A、被动流失 B、主动流失 C。
3. **讲验证路径**：先用漏斗确认购物车是流失环节，再用价格、品牌、时间、控制价格对比逐步排除和验证。
4. **讲核心发现**：价格差异不大，品牌维度差异更明显；时间会影响流失但不能单独解释品牌差异；同价位下 `masura` 比 `runail` 更容易主动流失。
5. **讲口径修正**：后来补做了 48 小时观察窗口，发现短期内 B 组占比更高，但固定风险阈值下品牌分层主结论仍基本稳定。
6. **讲建模反思**：初版 Logistic Regression AUC 0.8428，但发现使用了事后字段，存在目标泄露；重做 pre-cart 特征后 AUC 0.5773，说明真正可提前预测的行为信号还不够。
7. **讲业务意义**：品牌分层可以作为运营实验的候选依据，健康品牌测试加曝光，高风险品牌测试加购挽回和详情页治理，弱品牌高价段要谨慎验证。
8. **讲下一步**：从 session 粒度下沉到商品级特征，比如首次加购商品之前是否被浏览、浏览到加购的间隔，以提高提前预警能力。

---

## 历史探索阶段的原始项目结构

下面保留的是项目早期学习阶段的结构记录，用于说明分析过程；当前仓库导航和正式入口以前面的“仓库整理结果与导航”为准。

```text
eCommerce_Events_History/
├── data/
│   ├── raw/
│   │   └── Dec.csv
│   └── interim/
│       ├── 03_user_behavior_groups.csv
│       ├── 03_price_stats.csv
│       ├── 03_time_summary_point.csv
│       ├── 04_abc_brand_analysis.csv
│       ├── 05_brand_time_cross_analysis.csv
│       ├── 06_price_brand_group_analysis.csv
│       ├── 08_session_features.csv
│       ├── 09_pre_cart_features.csv
│       ├── 10_brand_quadrant_matrix.csv
│       ├── 11_user_behavior_groups_window_48h.csv
│       ├── 11_brand_quadrant_matrix_window_48h_median.csv
│       └── 11_brand_quadrant_matrix_window_48h_fixed_risk_1_5.csv
├── notebooks/
│   ├── 01_查看表格.ipynb
│   ├── 02_浏览加入购物车购买转化.ipynb
│   ├── 03_ab入购行为对比.ipynb
│   ├── 04_abc品牌维度分析.ipynb
│   ├── 05_品牌时间交叉分析me.ipynb
│   ├── 06_r品牌与m品牌价格品类流失分析.ipynb
│   ├── 07_项目总结与业务建议.ipynb
│   ├── 08_logistic_regression建模分析.ipynb
│   ├── 09_logistic_regression建模复习.ipynb
│   └── 10_品牌四象限矩阵.ipynb
├── reports/
│   ├── 02_user_funnel.png
│   ├── 03_price_metrics_comparison.png
│   ├── 03_time_point_distribution1.png
│   ├── 05_brand_time_cross_analysis.png
│   ├── 06_price_brand_group_analysis.png
│   ├── 07_brand_abc_stacked_bar.png
│   ├── 07_brand_risk_ratio.png
│   ├── 08_logistic_regression_results.png
│   ├── 10_brand_quadrant_matrix.png
│   ├── eCommerce_brand_quadrant_excel_practice.xlsx
│   ├── first_brand.pbix
│   └── user_funnel.html
├── scripts/
│   ├── build_windowed_user_behavior_groups.py
│   ├── compare_original_vs_windowed_groups.py
│   └── build_brand_quadrant_matrix.py
├── sql/
│   ├── 00_basic_checks.sql
│   ├── 01_event_funnel.sql
│   ├── 02_build_03_user_behavior_groups.sql
│   ├── 03_price_time_distribution.sql
│   ├── 04_brand_abc_analysis.sql
│   ├── 05_brand_time_price_checks.sql
│   ├── 06_brand_quadrant_matrix.sql
│   ├── 07_build_11_user_behavior_groups_window_48h.sql
│   └── README.md
├── README.md
├── worklog.md
└── requirements.txt
```

---

## 技术栈和方法

- Python
- Pandas / NumPy
- Matplotlib / Seaborn / Plotly
- Scikit-learn
- 漏斗分析
- A/B/C 分组对比
- 品牌结构分析
- 时间交叉分析
- 控制变量对比
- Logistic Regression
- 目标泄露检查
- 固定观察窗口 cohort
- 稳健性验证
- Excel 交付表
- Power BI 看板
- DAX Measure
- 动态筛选口径

---

## 局限性

1. 数据只覆盖 2019 年 12 月，无法判断长期趋势和季节性。
2. 数据来自化妆品品类，结论不一定能直接迁移到其他品类。
3. 缺少用户画像、评价、库存、优惠券、广告曝光、搜索词等上下文。
4. A/B/C 分组是基于行为结果构造的分析口径，不等同于严格因果实验。
5. 原 `03_user_behavior_groups.csv` 是全月事件结果口径，存在月末右截断和历史购物车左截断风险；已补充 48 小时窗口口径做稳健性检查。
6. 品牌差异只能说明不同品牌在当前数据口径下的结果不同，不能直接证明差异来自产品力、口碑或用户信任。
7. 初版模型存在目标泄露，已在复测中识别并修正，但也说明模型上线前必须重新定义预测时点。
8. pre-cart session 特征粒度偏粗，同一个 session 下多个商品共享同一组特征，后续应构造商品级行为特征。

---

## 当前项目状态

这个项目已经可以作为一个完整的数据分析实习作品来讲：

- 有明确业务问题。
- 有可解释的数据口径。
- 有逐步验证和排除过程。
- 有图表和中间数据支撑。
- 有业务建议。
- 有对模型目标泄露的反思。
- 有 Excel 和 Power BI 交付练习，能说明如何把分析结果整理成业务可读表和动态看板。
- 有清楚的下一步改进方向。

下一步最值得推进的是：围绕“首次加购商品”构造商品级 pre-cart 特征，把问题从“session 是否有购买倾向”推进到“用户对这个具体商品是否有足够购买意图”。

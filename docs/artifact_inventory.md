# 项目成果清单与处理决策

## 1. 正式版本（本轮新增）

| 目录/文件 | 定位 | 验收方式 |
|---|---|---|
| `docs/` | 立项、数据/指标字典、成果分层 | 人工审阅口径是否完整 |
| `sql/formal/` | 只读、可单独验证的 SQL | PostgreSQL 只读执行 |
| `scripts/run_formal_validation.py` | 执行 SQL、Python 独立复核、导出证据 | 对账结果无超阈值差异 |
| `notebooks/11_正式分析与验证.ipynb` | 正式、可重跑的分析入口 | 无密码、可顺序运行 |
| `reports/data_exports/` | Excel/Power BI/报告共同数据源 | 文件行数和指标对账 |
| `reports/data_quality_report.md` | 数据可信度和限制 | 与 SQL 输出一致 |
| `reports/management_onepager_source.md`、`management_report_artifact.json` | 管理层答案优先报告源与可验证快照 | 结构、来源和关键数字校验 |
| `outputs/formal_delivery/eCommerce_brand_priority_formal.xlsx` | 正式 Excel 交付 | 公式、阈值、品牌分类和总量对账 |
| `reports/power_bi_formal_spec.md`、`power_bi_measures.dax` | Power BI 两页方案与正式度量值 | 在 Power BI Desktop 可用后执行切片器 QA |

## 2. 保留为探索/学习过程

| 成果 | 决策 | 原因 |
|---|---|---|
| `notebooks/01`—`07` | 保留，不作为正式口径 | 展示从事件探索到业务结论的学习过程，但存在粒度混用和过度解释 |
| `notebooks/08`—`09` | 保留为建模练习 | 不是当前业务交付重点；随机按行切分存在同会话泄露风险 |
| `notebooks/10*` | 保留为四象限探索 | 使用旧口径/中点阈值，正式版改用完整 48 小时队列 |
| `reports/02`—`10` 图片与 HTML | 标为旧版图表 | 图表是历史输出，不删除；不再作为正式结论证据 |
| `reports/eCommerce_brand_quadrant_excel_practice.xlsx` | 保留为 Excel 练习版 | 只有 A/C，缺少占多数的 B；总计口径混合 |
| `reports/first_brand.pbix` | 保留为 Power BI 第一版 | 页面可用但主要展示明确结果子样本，缺少总体 48 小时 KPI |

## 3. 需要停止复用的旧口径

- `03_user_behavior_groups.csv`：A/B/C 不是严格的“加购后”结果，购买可能早于加购或没有加购；不用于正式结论。
- 旧漏斗中的“人数”标签：底层是 `user_id × product_id` 或其他非用户粒度时必须重命名。
- `C/A risk ratio`：正式名称改为“移除/购买比”。
- 由 UTC 小时直接得出的早晚时段运营建议：在业务时区未知时废弃。
- “品牌是根因”“可直接提升 GMV/ROI”等表述：改为待核查假设或实验建议。

## 4. 为什么不覆盖旧文件

企业项目需要审计轨迹。旧文件能证明探索过程，新文件能证明最终标准；直接覆盖会丢失口径演进，也不利于面试时解释“发现问题—修正—验证”的过程。

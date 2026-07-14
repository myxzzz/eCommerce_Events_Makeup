# 数据字典

## 1. 原始事件表 `makeup_consumer_events.dec`

一行代表一次用户行为事件。事件时间文本按 UTC 解释，正式 SQL 会显式执行 `SET TIME ZONE 'UTC'`。

| 字段 | 含义 | 主要质量风险 |
|---|---|---|
| `event_time` | 事件发生时间 | 原表为文本；若依赖数据库会话时区，显示时间可能漂移 |
| `event_type` | `view`、`cart`、`remove_from_cart`、`purchase` | 事件存在不完整链路，不能假设每次购买前都有本月浏览和加购 |
| `product_id` | 商品标识 | 需与会话一起确定主分析单元 |
| `category_id` | 品类标识 | 与 `category_code` 的缺失情况可能不同 |
| `category_code` | 品类层级文本 | 字面值 `NaN/null/none` 按缺失处理，不能据此删除整行 |
| `brand` | 品牌 | 字面值 `NaN/null/none` 按未知品牌处理；品牌分析需单独报告覆盖率 |
| `price` | 事件记录价格 | 币种未知；正式报告只称“价格”，不称“人民币/元” |
| `user_id` | 用户标识 | 一个用户可跨多个会话、商品和事件 |
| `user_session` | 会话标识 | 存在字面值 `NaN`；正式会话分析将其视为无效键并排除，避免把不同用户串成同一会话 |

候选事件键为全部业务字段组合，但数据未提供稳定的事件 ID，因此重复检查只能识别“完全相同记录”，不能证明两条相同记录一定是误重复。

## 2. 48 小时首次观测加购表 `11_user_behavior_groups_window_48h`

一行代表 `user_session × product_id` 在 2019 年 12 月数据中的首次观测加购。它不是用户历史上的首次加购。

| 字段 | 含义 |
|---|---|
| `user_session`、`product_id` | 联合分析键 |
| `user_id` | 加购事件对应用户 |
| `brand`、`category_code`、`category_id` | 首次观测加购事件的商品属性 |
| `price` | 首次观测加购时记录的价格 |
| `first_cart_time` | 本数据窗口内首次观测到该会话—商品加购的时间 |
| `window_end_time` | `first_cart_time + 48 hours` |
| `has_purchase_48h` | 窗口内是否出现购买 |
| `has_remove_48h` | 窗口内是否出现移除 |
| `group_type` | A=购买；C=未购买但移除；B=两者都没有 |
| `event_type_window` | 窗口内观察到的事件类型集合 |
| `first_followup_time` | 首个后续事件时间 |

## 3. 正式品牌指标导出 `reports/data_exports/brand_metrics_48h.csv`

一行代表一个满足最小样本要求的已知品牌。

| 字段 | 含义 |
|---|---|
| `brand_cohort_count` | 该品牌 A+B+C 的完整 48 小时加购样本数 |
| `purchase_count`、`unresolved_count`、`remove_count` | A、B、C 数量 |
| `clear_outcome_count` | A+C，有明确购买或移除结果的数量 |
| `brand_share_pct` | 该品牌样本占全部完整样本的比例 |
| `purchase_rate_pct` | A/(A+B+C) |
| `unresolved_rate_pct` | B/(A+B+C) |
| `remove_rate_pct` | C/(A+B+C) |
| `clear_purchase_rate_pct` | A/(A+C)，只反映明确结果子样本 |
| `remove_to_purchase_ratio` | C/A，描述性比值，不是概率 |
| `volume_band` | 相对符合条件品牌中位数的高/低覆盖量 |
| `risk_band` | 比值是否达到项目启发式阈值 1.5 |
| `priority_quadrant` | 覆盖量与比值组合的运营优先级 |

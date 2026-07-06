# SQL Files

这些 SQL 文件把项目里散落在 notebook 和 Python 脚本中的数据库逻辑拆出来，方便直接在 PostgreSQL 客户端里学习和运行。

默认数据库对象：

```sql
schema: makeup_consumer_events
raw table: makeup_consumer_events.dec
original grouped table: makeup_consumer_events."03_user_behavior_groups"
48h grouped table: makeup_consumer_events."11_user_behavior_groups_window_48h"
```

## 建议学习顺序

| 文件 | 作用 | 主要 SQL 知识点 |
|---|---|---|
| `00_basic_checks.sql` | 查看原始表结构、行数、事件分布 | `SELECT`, `COUNT`, `GROUP BY`, `ORDER BY` |
| `01_event_funnel.sql` | 浏览、加购、购买漏斗 | `WITH`, `STRING_AGG`, `FILTER`, `NULLIF` |
| `02_build_03_user_behavior_groups.sql` | 用 SQL 复刻旧 A/B/C 分组表 | `ROW_NUMBER`, `ARRAY_AGG`, `BOOL_OR`, `CASE WHEN`, `CREATE TABLE AS` |
| `03_price_time_distribution.sql` | A/B/C 价格和小时分布 | `PERCENTILE_CONT`, `EXTRACT`, 窗口占比 |
| `04_brand_abc_analysis.sql` | 品牌在 A/B/C 组里的占比 | 品牌清洗、分组占比、宽表转换 |
| `05_brand_time_price_checks.sql` | runail vs masura 的时间和价格带对比 | `CASE WHEN`, 条件聚合, 风险比 |
| `06_brand_quadrant_matrix.sql` | 品牌四象限指标表 | 多层 CTE, 中位数阈值, 固定阈值 |
| `07_build_11_user_behavior_groups_window_48h.sql` | 48 小时固定观察窗口分组表 | `DISTINCT ON`, `LEFT JOIN`, `BOOL_OR`, 索引 |

## 日常怎么用 SQL

一般日常分析里，SQL 负责三类事情：

1. **取数**：从数据库里筛选需要的行和列。
2. **聚合**：按用户、商品、品牌、时间等维度做统计。
3. **建中间表**：把稳定口径保存成一张表，后续 notebook 或 BI 直接读取。

典型流程：

```text
先用 00 看表结构
再用 01/03/04 做探索查询
如果口径稳定，用 02 或 07 建中间表
最后用 05/06 做业务分析聚合
```

## 在 PostgreSQL 里运行

在 pgAdmin / DBeaver 里打开对应 `.sql` 文件，直接执行即可。

在命令行里可以用：

```bash
psql -h localhost -U postgres -d postgres -f sql/00_basic_checks.sql
```

如果 SQL 文件里有 `DROP TABLE` / `CREATE TABLE`，说明它会修改数据库对象。只想学习查询时，优先运行只包含 `SELECT` 的文件。


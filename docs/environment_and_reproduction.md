# 环境与复现说明

## 运行环境

- 操作系统：Windows x64，PowerShell。
- 推荐 Python：`D:\conda-envs\data-learning\python.exe`，Python 3.13.7。
- PostgreSQL：`localhost:5432`，数据库 `postgres`，用户 `postgres`。
- 正式源表：`makeup_consumer_events.dec`。
- Python 依赖：见根目录 `requirements.txt`。

不要把数据库密码写入代码、Notebook、日志或版本库。可使用本机 PostgreSQL 安全配置、环境变量或当前用户的认证方式；`.env.example` 只列变量名。

## 数据前提

正式 SQL 默认源表已经存在，并包含：

`event_time`、`event_type`、`product_id`、`category_id`、`category_code`、`brand`、`price`、`user_id`、`user_session`。

正式流程不修改源表。所有 `sql/formal/*.sql` 都是只读查询，不包含 `CREATE`、`INSERT`、`UPDATE`、`DELETE`、`DROP` 或 `ALTER`。

## 推荐执行顺序

### 1. 核对 Python 环境

```powershell
& 'D:\conda-envs\data-learning\python.exe' --version
& 'D:\conda-envs\data-learning\python.exe' -m pip check
```

如需重新安装依赖，应先创建或激活专用环境，再执行：

```powershell
& 'D:\conda-envs\data-learning\python.exe' -m pip install -r requirements.txt
```

这一步会改动环境，不是每次复现都需要执行。

### 2. 运行 SQL 与跨工具对账

```powershell
& 'D:\conda-envs\data-learning\python.exe' scripts\run_formal_validation.py
```

脚本会依次执行 `sql/formal/` 的正式查询，写入 `reports/data_exports/`，再用 Python 从明细重新聚合并生成 `reconciliation_summary.csv`。预期结果：25 项检查、0 个错误；旧 CSV 的无效会话差异作为警告披露。

### 3. 生成正式图表和文本报告源

```powershell
& 'D:\conda-envs\data-learning\python.exe' scripts\build_formal_artifacts.py
```

输出包括 `reports/formal_charts/`、`reports/data_quality_report.md`、`reports/management_onepager_source.md` 和 `reports/chart_map.md`。

### 4. 生成并执行正式 Notebook

```powershell
& 'D:\conda-envs\data-learning\python.exe' scripts\build_formal_notebook.py
& 'D:\conda-envs\data-learning\python.exe' -m jupyter nbconvert --execute --to notebook --inplace notebooks\11_正式分析与验证.ipynb
```

Notebook 使用正式 CSV，不重新定义业务口径。执行后应有 8 个代码单元成功运行，且无错误输出。

### 5. 重建管理层报告快照

```powershell
& 'D:\conda-envs\data-learning\python.exe' scripts\build_management_report_artifact.py
```

输出 `reports/management_report_artifact.json`。该文件保存报告结构、受控数据快照和实际 SQL 来源；生成脚本只读取正式导出与 SQL，不连接或修改数据库。

### 6. Excel 与 Power BI

正式 Excel 已生成在：

`outputs/formal_delivery/eCommerce_brand_priority_formal.xlsx`

Power BI 需要在装有 Power BI Desktop 的机器上按 `reports/power_bi_formal_spec.md` 导入正式 CSV，并粘贴 `reports/power_bi_measures.dax` 中的度量值。完成后必须逐项验证：

- 页面总量与 `kpi_summary_48h.csv` 一致。
- 品牌筛选后使用分子/分母重算，不平均品牌率。
- 未知品牌覆盖限制可见。
- 24/48/72 小时窗口图使用共同队列。
- A+B+C 等于当前筛选范围的正式样本数。

## 最小验收清单

- `cohort_count = 772119`。
- A/B/C 分别为 `104696 / 511286 / 156137`，总和等于队列。
- 总体购买率、未明确处置率、移除率分别为 `13.5596% / 66.2185% / 20.2219%`。
- 已知品牌覆盖率为 `55.9880%`。
- 正式队列重复 `user_session × product_id` 超额行 = 0。
- 标签矛盾行 = 0。
- SQL/Python 对账错误数 = 0。
- Notebook 无错误输出。
- Excel 公式错误扫描 = 0。

## 常见问题

### 数据库连接失败

确认 PostgreSQL 服务、host、port、database、user 和本机认证配置。不要为了方便把密码补进脚本。

### SQL 结果和旧 CSV 相差 369 行

这是已知差异：旧 CSV 包含字面值 `user_session='NaN'` 的样本。正式流程将其视为无效会话键，避免跨用户串联。

### 月末样本为什么少了

首次加购后不足 48 小时的数据无法判断完整结果，因此 19,231 个尾部候选被排除。这是右截断控制，不是数据丢失错误。

### 为什么品类分析很弱

`category_code` 在正式队列中几乎全部缺失。可以保留 `category_id` 做匿名分组，但不能把它解释成可读业务品类。

# RAG-gq 项目说明（中文）

[中文](./README.md) | [English](./README_EN.md)

本项目是一个面向**企业研报/年报问答**的 RAG（Retrieval-Augmented Generation）实践工程，支持从 PDF 报告解析、结构化整理、分块、向量化，到问题问答的完整链路。

当前版本已完成一轮针对 `stock_data` 数据集的可运行修复，重点增强了：

- 多种解析入口（Docling / MinerU）
- 对缺失 `subset.csv` 的降级兼容
- Agicto（OpenAI 兼容）在 embedding / 问答 / rerank 链路的接入
- 检索与重排过程中的异常兜底，避免流程中断

---

## 1. 项目结构

```text
RAG-gq/
├─ src/                      # 核心代码
│  ├─ pipeline.py            # 主流程编排
│  ├─ pdf_mineru.py          # MinerU 解析接口
│  ├─ parsed_reports_merging.py
│  ├─ text_splitter.py
│  ├─ ingestion.py           # 向量库/BM25构建
│  ├─ retrieval.py           # 向量检索/混合检索
│  ├─ reranking.py           # LLM重排
│  ├─ questions_processing.py# 问答主流程
│  └─ api_requests.py        # 模型调用适配层
├─ data/
│  ├─ stock_data/            # 当前主要示例数据
│  └─ test_set/              # 小型测试数据
├─ docs/
│  └─ notes/                 # 过程说明与规范文档
├─ requirements.txt
└─ README.md
```

---

## 2. 环境准备

建议 Python 3.12，Windows PowerShell 示例：

```bash
python -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 3. 配置文件（`.env`）

项目通过 `.env` 管理模型与平台参数。你当前主要使用 Agicto：

- `AGICTO_API_KEY`
- `AGICTO_BASE_URL`
- `AGICTO_CHAT_MODEL`（如 `deepseek-v4-flash`）

并建议显式配置：

- `EMBEDDING_PROVIDER=agicto`
- `AGICTO_EMBEDDING_MODEL=text-embedding-ada-002`（或你的可用模型）
- `RERANK_PROVIDER=agicto`（可选，未配置时会按默认逻辑回退）
- `RERANK_MODEL`（可选；不配时可复用 `AGICTO_CHAT_MODEL`）

MinerU 解析需要：

- `MINERU_API_KEY`
- `MINERU_SUBMIT_URL`
- `MINERU_RESULT_URL_TEMPLATE`

---

## 4. 数据与提交策略

### 4.1 当前示例数据

`data/stock_data/` 中包含：

- `questions.json`：问题输入
- `pdf_reports/`：报告原文 PDF（用于可复现）
- `answers_*.json`：不同轮次结果文件

### 4.2 `.gitignore` 说明

默认忽略了中间产物目录（如 `debug_data/`、`databases/`），避免仓库膨胀。若需要提交 PDF 来源，可使用 `git add -f data/stock_data/pdf_reports/` 强制加入。

---

## 5. 运行方式

### 5.1 直接运行主流程

```bash
python -m src.pipeline
```

`pipeline.py` 内可通过 `start_step` 控制从哪一步开始。

### 5.2 典型处理链路

1. 解析 PDF（Docling 或 MinerU）
2. 规整为每页 JSON（`02_merged_reports`）
3. 导出 Markdown（`03_reports_markdown`）
4. Markdown 分块（`chunked_reports`）
5. 构建向量库（`vector_dbs`）
6. 执行问题问答并输出 `answers_*.json`

### 5.3 启动 RAG 可视化界面（Streamlit）

```bash
streamlit run .\app.py
```

默认访问地址：`http://localhost:8501`

界面能力：

- 多数据集自动发现（`data/*`）
- 全库检索或按公司检索
- 默认开启 LLM 重排（可关闭）
- 答案结果 + 调试信息面板（检索参数、耗时、原始JSON）

---

## 6. 当前已修复的关键问题（摘要）

本轮已完成的核心修复包括：

1. **embedding provider 对齐**
   - 避免向量化阶段默认误走 DashScope。
2. **问题字段兼容**
   - 兼容 `text/kind` 与 `question/schema` 两套输入字段。
3. **`pages` 缺失兼容**
   - 检索时若文档只有 `chunks`，自动回退，不再 `KeyError: 'pages'`。
4. **LLM 重排异常降级**
   - 重排失败时回落到默认分数，不中断问答。
5. **Rerank provider 可走 Agicto**
   - 减少对 DashScope 的依赖，支持统一平台。

---

## 7. 常见问题（FAQ）

### Q1：`subset.csv not found ... fallback to new_challenge_pipeline=False`
这是兼容降级提示，不一定是错误。若你使用的是 `questions.json (text/kind)`，流程仍可继续。

### Q2：为什么会出现 DashScope 报错？
通常是某条子链路（常见是 rerank）仍走默认 DashScope。请检查 `RERANK_PROVIDER` / `EMBEDDING_PROVIDER` 与代码默认值是否一致。
### Q3：`git push` 的 HTTPS 失败（connection reset）
在部分网络环境下 443 不稳定，可切换远端到 SSH：

```bash
git remote set-url origin git@github.com:<your-username>/<repo>.git
git push -u origin main
```

---

## 8. 开发说明

- 当前代码以“可运行、可调试”为优先，非严格生产化工程。
- 项目内代码改动默认遵循：
  - `docs/notes/code-change-comment-guidelines.md`

---

## 9. 致谢

本仓库基于 RAG 竞赛思路持续演化，已结合本地数据与平台配置做了多轮工程化适配。

如果你要继续扩展（多数据集、多模型评测、可视化评估、服务化部署），建议下一步补充：

- 标准化配置层（按 provider 解耦）
- 统一日志与指标埋点
- 最小回归测试集（至少覆盖 1 条完整链路）

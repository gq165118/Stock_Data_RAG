# RAG-gq（中文）

[中文](./README.md) | [English](./README_EN.md)

`RAG-gq` 是一个面向企业研报/年报问答的 RAG 项目，提供从 PDF 解析到问答输出的完整链路，适合用于：

- 企业知识库问答原型
- 多文档检索与证据定位
- RAG 策略实验（检索、重排、提示词）

## 项目能力

- PDF 解析：支持 Docling 与 MinerU
- 文档规整：解析结果统一为页面/文本结构
- 检索：向量检索，支持全库检索与按公司检索
- 重排：可选 LLM reranking（默认可开启）
- 问答：结构化 schema 输出（string / boolean / number / name / names）
- UI：内置 Streamlit 可视化界面（含调试信息面板）

## 目录结构

```text
RAG-gq/
├─ src/
│  ├─ pipeline.py
│  ├─ retrieval.py
│  ├─ reranking.py
│  ├─ questions_processing.py
│  ├─ ingestion.py
│  └─ ...
├─ data/
│  ├─ stock_data/
│  └─ test_set/
├─ docs/
├─ app.py
└─ requirements.txt
```

## 快速开始

### 1) 环境安装

```bash
python -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) 配置 `.env`

最少需要配置（以 Agicto 为例）：

- `AGICTO_API_KEY`
- `AGICTO_BASE_URL`
- `AGICTO_CHAT_MODEL`
- `EMBEDDING_PROVIDER=agicto`

建议可选配置：

- `AGICTO_EMBEDDING_MODEL`
- `RERANK_PROVIDER=agicto`
- `RERANK_MODEL`（不填时可复用 `AGICTO_CHAT_MODEL`）

如使用 MinerU 解析，还需：

- `MINERU_API_KEY`
- `MINERU_SUBMIT_URL`
- `MINERU_RESULT_URL_TEMPLATE`

## 运行方式

### 方式 A：运行主流程

```bash
python -m src.pipeline
```

典型流程：

1. 解析 PDF
2. 报告规整
3. 导出 Markdown
4. 文本分块
5. 构建向量库
6. 执行问答并输出结果

### 方式 B：运行可视化界面

```bash
streamlit run .\app.py
```

启动后请以终端输出的地址为准（通常是本地 `8501` 端口）。

## 数据说明

示例数据位于 `data/stock_data/`，包括：

- `questions.json`：输入问题
- `pdf_reports/`：示例 PDF 来源
- `answers_*.json`：历史输出样例

`.gitignore` 默认忽略 `debug_data` / `databases` 等中间产物，避免仓库体积膨胀。

## 当前状态

项目已完成一轮稳定性增强，重点包括：

- provider 链路对齐（embedding / rerank / qa）
- `text/kind` 与 `question/schema` 双格式兼容
- `pages` 缺失场景回退兼容
- reranking 异常降级，避免流程中断
- Streamlit UI 多数据集选择与调试面板

## 适用边界

本仓库当前以“可运行、可调试、可演示”为优先，不是完整生产化模板。

如果你要用于生产环境，建议补充：

- 完整测试与回归基线
- 统一日志/监控/追踪
- 配置中心与密钥治理
- 更细粒度的错误恢复策略

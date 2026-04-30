# `src/pipeline.py` 学习笔记

> 面向有 C++ 基础、Python 不熟悉的学习者。目标：精简理解 Python 语法和本文件在 RAG 项目中的职责。

## 1. 文件整体职责

`pipeline.py` 是项目的流程总控文件，负责把各模块串成完整 RAG 流程：

```text
PDF 报告 → 解析 JSON → 规整文本 → 文本分块 → 建检索库 → 问答生成
```

它主要包含：

- `PipelineConfig`：路径配置。
- `RunConfig`：运行参数配置。
- `Pipeline`：流程编排类。
- 多套实验配置。
- `if __name__ == "__main__"` 脚本入口。

---

## 2. 导入与基础语法

```python
from dataclasses import dataclass
from pathlib import Path
from pyprojroot import here
import logging
import json
import pandas as pd
```

要点：

- `import` 类似 C++ 的 `#include`，但 Python 是运行时加载模块。
- `Path` 类似 C++17 的 `std::filesystem::path`。
- `pandas as pd` 类似 C++ 命名空间别名。
- `from src.xxx import Yyy` 表示从项目模块导入类。

---

## 3. `PipelineConfig`：路径配置

作用：集中管理输入、输出路径。

```python
@dataclass
class PipelineConfig:
    def __init__(self, root_path: Path, subset_name: str = "subset.csv", ...):
        self.root_path = root_path
        suffix = "_ser_tab" if serialized else ""
        self.subset_path = root_path / subset_name
        self.answers_file_path = root_path / f"answers{config_suffix}.json"
```

要点：

- `@dataclass` 通常自动生成 `__init__`，但这里手写了 `__init__`。
- `root_path: Path` 是类型标注，类似 C++ 的 `std::filesystem::path root_path`，但 Python 默认不强制类型。
- `self` 类似 C++ 的 `this`，但必须显式写。
- `Path / "xxx"` 是路径拼接。
- `f"answers{config_suffix}.json"` 是 f-string。
- `a if cond else b` 类似 C++ 的 `cond ? a : b`。

---

## 4. `RunConfig`：运行参数配置

```python
@dataclass
class RunConfig:
    use_serialized_tables: bool = False
    parent_document_retrieval: bool = False
    use_vector_dbs: bool = True
    llm_reranking: bool = False
    parallel_requests: int = 1
    api_provider: str = "dashscope"
    answering_model: str = "qwen-turbo-latest"
```

作用：控制流程怎么跑。

| 类 | 职责 |
|---|---|
| `PipelineConfig` | 文件和目录路径 |
| `RunConfig` | 功能开关、模型、并发、检索参数 |

要点：

- 这是 `@dataclass` 的典型用法，会自动生成 `__init__`。
- `字段名: 类型 = 默认值` 类似 C++ struct 成员默认值。
- Python 布尔值是 `True` / `False`。

---

## 5. `Pipeline.__init__`

```python
class Pipeline:
    def __init__(self, root_path: Path, ..., run_config: RunConfig = RunConfig()):
        self.run_config = run_config
        self.paths = self._initialize_paths(...)
        self._convert_json_to_csv_if_needed()
```

作用：

1. 保存运行配置到 `self.run_config`。
2. 初始化路径配置到 `self.paths`。
3. 自动检查是否需要把 `subset.json` 转成 `subset.csv`。

注意：`run_config: RunConfig = RunConfig()` 使用对象作为默认参数，Python 中这类默认值在函数定义时创建一次，复杂场景可能有共享对象风险。

---

## 6. `_initialize_paths`

```python
def _initialize_paths(...) -> PipelineConfig:
    return PipelineConfig(
        root_path=root_path,
        serialized=self.run_config.use_serialized_tables,
        config_suffix=self.run_config.config_suffix
    )
```

要点：

- `-> PipelineConfig` 是返回值类型标注，类似 C++11 尾置返回类型。
- `_` 开头是内部方法约定，不是强制私有。
- `root_path=root_path` 左边是被调用函数参数名，右边是当前局部变量。

作用：把 `RunConfig` 中影响路径的参数传给 `PipelineConfig`。

---

## 7. `_convert_json_to_csv_if_needed`

```python
if json_path.exists() and not csv_path.exists():
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)
    except Exception as e:
        print(f"Error converting JSON to CSV: {str(e)}")
```

要点：

- 没有 `return` 时默认返回 `None`，类似 C++ `void`。
- `Path.exists()` 判断路径是否存在。
- `with open(...) as f` 类似 C++ RAII，会自动关闭文件。
- `json.load(f)` 从文件对象读取 JSON。
- `pd.DataFrame(data)` 转表格。
- `to_csv(..., index=False)` 保存 CSV，不写 Pandas 行索引。

作用：兼容只有 `subset.json`、没有 `subset.csv` 的数据集。

---

## 8. `download_docling_models`

```python
@staticmethod
def download_docling_models():
    parser = PDFParser(output_dir=here())
    parser.parse_and_export(input_doc_paths=[here() / "src/dummy_report.pdf"])
```

要点：

- `@staticmethod` 类似 C++ `static` 成员函数，不需要 `self`。
- `[path]` 是包含一个元素的列表。

作用：用 dummy PDF 预热 Docling，提前下载/初始化 PDF 解析模型。

---

## 9. PDF 解析

### 顺序解析

```python
pdf_parser = PDFParser(
    output_dir=self.paths.parsed_reports_path,
    csv_metadata_path=self.paths.subset_path
)
pdf_parser.debug_data_path = self.paths.parsed_reports_debug_path
pdf_parser.parse_and_export(doc_dir=self.paths.pdf_reports_dir)
```

作用：

```text
pdf_reports/ → debug_data/01_parsed_reports/
```

要点：`pdf_parser.debug_data_path = ...` 是动态设置对象属性。

### 并行解析

```python
input_doc_paths = list(self.paths.pdf_reports_dir.glob("*.pdf"))
pdf_parser.parse_and_export_parallel(
    input_doc_paths=input_doc_paths,
    optimal_workers=max_workers,
    chunk_size=chunk_size
)
```

要点：

- `Path.glob("*.pdf")` 查找当前目录下所有 PDF，不递归。
- `list(...)` 把可迭代结果转成列表。
- `max_workers` 和 `chunk_size` 控制并行粒度。

---

## 10. 表格序列化与报告规整

### `serialize_tables`

```python
serializer = TableSerializer()
serializer.process_directory_parallel(self.paths.parsed_reports_path, max_workers=max_workers)
```

作用：对解析后的表格做序列化，使财报表格更适合检索和 LLM 理解。

区分：

- `serialize_tables()`：实际生成表格序列化结果。
- `RunConfig(use_serialized_tables=True)`：让后续流程使用序列化表格结果。

### `merge_reports`

```python
ptp = PageTextPreparation(use_serialized_tables=self.run_config.use_serialized_tables)
_ = ptp.process_reports(
    reports_dir=self.paths.parsed_reports_path,
    output_dir=self.paths.merged_reports_path
)
```

作用：把复杂解析 JSON 规整成页级文本结构。

```text
01_parsed_reports/ → 02_merged_reports/
```

`_ = ...` 表示返回值不关心。

### `export_reports_to_markdown`

作用：导出 Markdown，主要用于人工复核解析质量，不是主问答流程必需步骤。

---

## 11. 文本分块与检索库

### `chunk_reports`

```python
serialized_tables_dir = None
if include_serialized_tables:
    serialized_tables_dir = self.paths.parsed_reports_path

text_splitter.split_all_reports(
    self.paths.merged_reports_path,
    self.paths.documents_dir,
    serialized_tables_dir
)
```

作用：

```text
02_merged_reports/ → databases/chunked_reports/
```

要点：

- `None` 表示没有值，接近 `std::nullopt` / `nullptr` 场景。
- RAG 需要分块，因为整份报告太长，检索粒度也太粗。

### `create_vector_dbs`

```python
vdb_ingestor = VectorDBIngestor()
vdb_ingestor.process_reports(input_dir, output_dir)
```

作用：把 chunk 文本向量化，建立语义检索库。

```text
chunked_reports/ → vector_dbs/
```

### `create_bm25_db`

```python
bm25_ingestor = BM25Ingestor()
bm25_ingestor.process_reports(input_dir, output_file)
```

作用：建立关键词检索库。

| 检索方式 | 特点 |
|---|---|
| 向量检索 | 语义相似，适合同义改写 |
| BM25 | 关键词匹配，适合术语、数字、专有名词 |

---

## 12. `process_parsed_reports`

```python
def process_parsed_reports(self):
    self.merge_reports()
    self.export_reports_to_markdown()
    self.chunk_reports()
    self.create_vector_dbs()
```

作用：处理已经解析好的报告，不重新解析 PDF，也不生成最终答案。

流程：

```text
01_parsed_reports/ → 02_merged_reports/ → chunked_reports/ → vector_dbs/
```

---

## 13. `_get_next_available_filename`

```python
if not base_path.exists():
    return base_path

stem = base_path.stem
suffix = base_path.suffix
parent = base_path.parent

counter = 1
while True:
    new_filename = f"{stem}_{counter:02d}{suffix}"
    new_path = parent / new_filename
    if not new_path.exists():
        return new_path
    counter += 1
```

作用：避免覆盖已有答案文件。

要点：

- `Path.stem`：不带扩展名的文件名。
- `Path.suffix`：扩展名。
- `Path.parent`：父目录。
- `{counter:02d}` 表示至少两位，不足补 0，如 `01`。
- Python 没有 `counter++`，用 `counter += 1`。

示例：

```text
answers.json 已存在 → answers_01.json
answers_01.json 已存在 → answers_02.json
```

---

## 14. `process_questions`

```python
processor = QuestionsProcessor(
    vector_db_dir=self.paths.vector_db_dir,
    documents_dir=self.paths.documents_dir,
    questions_file_path=self.paths.questions_file_path,
    subset_path=self.paths.subset_path,
    parent_document_retrieval=self.run_config.parent_document_retrieval,
    llm_reranking=self.run_config.llm_reranking,
    top_n_retrieval=self.run_config.top_n_retrieval,
    parallel_requests=self.run_config.parallel_requests,
    api_provider=self.run_config.api_provider,
    answering_model=self.run_config.answering_model,
)

output_path = self._get_next_available_filename(self.paths.answers_file_path)
_ = processor.process_all_questions(output_path=output_path, ...)
```

作用：完整问答入口。

```text
questions.json → 检索 vector_dbs / chunked_reports → LLM → answers_xxx.json
```

关键配置：

| 配置 | 影响 |
|---|---|
| `parent_document_retrieval` | 是否扩展到父文档 |
| `llm_reranking` | 是否让 LLM 对候选结果重排序 |
| `top_n_retrieval` | 最终保留多少条上下文 |
| `parallel_requests` | 并发处理问题数量 |
| `api_provider` | 模型服务商 |
| `answering_model` | 具体回答模型 |

注意：它假设向量库/chunk 已经存在，不负责创建。

---

## 15. 多套配置与脚本入口

文件后半部分定义多套 `RunConfig`，例如：

```python
base_config = RunConfig(...)
max_config = RunConfig(...)
max_nst_o3m_config = RunConfig(...)
```

作用：保存不同 RAG 策略，方便实验对比。

`configs` 是字典，类似 `std::unordered_map<std::string, RunConfig>`：

```python
configs = {
    "base": base_config,
    "max": max_config,
    "max_nst_o3m": max_nst_o3m_config,
}
```

脚本入口：

```python
if __name__ == "__main__":
    root_path = here() / "data" / "test_set"
    pipeline = Pipeline(root_path, run_config=max_nst_o3m_config)
    pipeline.parse_pdf_reports_sequential()
    pipeline.serialize_tables(max_workers=5)
    pipeline.merge_reports()
    pipeline.export_reports_to_markdown()
    pipeline.chunk_reports()
    pipeline.create_vector_dbs()
    pipeline.process_questions()
```

要点：

- `if __name__ == "__main__"` 类似脚本版 `main()`。
- 直接运行 `python src/pipeline.py` 时执行。
- 被其他文件 `import` 时不执行。

当前直接运行时使用：

```python
max_nst_o3m_config
```

核心参数：

```python
use_serialized_tables=False
parent_document_retrieval=True
llm_reranking=True
parallel_requests=4
answering_model="qwen-turbo-latest"
config_suffix="_max_nst_o3m"
```

最终答案类似：

```text
answers_max_nst_o3m.json
```

若已存在，则自动生成：

```text
answers_max_nst_o3m_01.json
```

---

## 16. 总结

`pipeline.py` 的核心价值是流程编排：

```text
配置路径 → 配置运行参数 → 解析 PDF → 表格处理 → 合并文本 → 分块 → 建检索库 → 问答生成
```

它不是 PDF 解析、向量化、问答算法的实现文件，而是把这些模块连接起来。

后续建议学习：

```text
src/questions_processing.py
```

因为 `process_questions()` 已经进入真正的检索和 LLM 问答逻辑。

# 问答流程调试速查

> 作用：精炼记录从测试问题到答案文件的主流程，便于后续调试 RAG 问答链路。

## 1. 运行入口

在测试数据目录执行：

```powershell
cd data\test_set
..\..\.venv312\Scripts\python.exe ..\..\main.py process-questions --config minimax
```

入口函数：

```text
main.py -> process_questions(config)
```

关键点：`Path.cwd()` 会把当前目录作为数据集根目录，所以命令应在 `data/test_set` 下运行。

## 2. 输入与输出

输入问题：

```text
data/test_set/questions.json
```

辅助数据：

```text
data/test_set/subset.csv
data/test_set/databases/chunked_reports/*.json
data/test_set/databases/vector_dbs/*.faiss
```

输出答案：

```text
data/test_set/answers_minimax_xx.json
data/test_set/answers_minimax_xx_debug.json
```

其中 debug 文件更适合调试，包含中间结果、模型信息和错误详情。

## 3. 主调用链

```text
main.py
  -> Pipeline.process_questions()
  -> QuestionsProcessor.process_all_questions()
  -> QuestionsProcessor.process_questions_list()
  -> QuestionsProcessor._process_single_question()
  -> QuestionsProcessor.process_question()
  -> QuestionsProcessor.get_answer_for_company()
  -> HybridRetriever / VectorRetriever 检索文本
  -> APIProcessor.get_answer_from_rag_context()
  -> Minimax / Kimi 生成结构化答案
  -> QuestionsProcessor._post_process_submission_answers()
  -> QuestionsProcessor._save_progress()
```

## 4. 核心处理步骤

1. `questions.json` 读取问题文本和答案类型。
2. `subset.csv` 根据问题文本匹配公司名。
3. `databases/vector_dbs` 加载 FAISS 向量库。
4. `databases/chunked_reports` 加载对应文本块。
5. 将问题转 embedding 后做向量检索。
6. 如配置开启 `llm_reranking`，对候选文本重新排序。
7. 将检索结果拼成 RAG 上下文。
8. 调用 Kimi/Minimax 生成结构化答案。
9. 校验引用页码并写出答案文件。

## 5. 建议调试断点

优先从这些位置看完整链路：

```text
main.py -> process_questions
src/pipeline.py -> Pipeline.process_questions
src/questions_processing.py -> _process_single_question
src/questions_processing.py -> get_answer_for_company
src/retrieval.py -> VectorRetriever.retrieve_by_company_name
src/retrieval.py -> HybridRetriever.retrieve_by_company_name
src/api_requests.py -> APIProcessor.get_answer_from_rag_context
src/api_requests.py -> BaseOpenAICompatibleProcessor.send_message
src/questions_processing.py -> _save_progress
```

## 6. 常见定位方向

- 问题没读到：看 `questions.json` 和 `_load_questions()`。
- 公司名没匹配到：看 `subset.csv` 和 `_extract_companies_from_subset()`。
- 向量库读取失败：看 `databases/vector_dbs` 和 `VectorRetriever._load_dbs()`。
- 检索结果不准：看 `retrieve_by_company_name()` 的 `distances`、`indices`、`retrieval_results`。
- 模型回答异常：看 `get_answer_from_rag_context()` 和 `send_message()` 中的 prompt、model、content。
- 输出格式异常：看 `_post_process_submission_answers()` 和 `_save_progress()`。

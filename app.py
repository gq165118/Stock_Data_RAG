import json
from pathlib import Path
import streamlit as st

from src.ui_service import RAGUIService


# add by gq [2026-05-04：新增RAG可视化界面入口，支持多数据集检索与问答调试]
st.set_page_config(page_title="RAG-gq UI", page_icon="🚀", layout="wide")

st.title("🚀 RAG-gq 企业知识问答界面")
st.caption("支持多数据集选择、检索调参、答案生成与调试信息查看")

service = RAGUIService(project_root=Path(__file__).resolve().parent)
datasets = service.discover_datasets()

if not datasets:
    st.error("未发现可用数据集。请确认 data/* 下存在 questions.json、databases/chunked_reports、databases/vector_dbs。")
    st.stop()

with st.sidebar:
    st.header("⚙️ 查询设置")

    dataset_name = st.selectbox("选择数据集", options=list(datasets.keys()), index=0)
    dataset_path = datasets[dataset_name]

    companies = service.list_companies(dataset_path)
    company_options = ["（全库检索）"] + companies
    selected_company = st.selectbox("选择公司（可选）", options=company_options, index=0)
    company_name = None if selected_company == "（全库检索）" else selected_company

    query = st.text_area(
        "输入问题",
        value="中芯国际在晶圆制造行业中的地位如何？",
        height=120,
    )

    schema = st.selectbox("答案类型 schema", options=["string", "boolean", "number", "name", "names"], index=0)

    st.subheader("🔎 检索参数")
    top_n = st.slider("返回文档数 top_n", min_value=1, max_value=20, value=10, step=1)
    llm_reranking = st.toggle("启用 LLM 重排", value=True)
    llm_reranking_sample_size = st.slider("重排候选数", min_value=5, max_value=50, value=20, step=1)
    return_parent_pages = st.toggle("返回父页内容", value=False)

    st.subheader("🤖 模型参数")
    api_provider = st.selectbox("问答 Provider", options=["agicto", "kimi", "minimax", "dashscope", "openai"], index=0)
    answering_model = st.text_input("问答模型", value="deepseek-v4-flash")

    search_clicked = st.button("🔍 检索文档", use_container_width=True)
    answer_clicked = st.button("🧠 生成答案", use_container_width=True)

if "retrieval_results" not in st.session_state:
    st.session_state["retrieval_results"] = []
if "retrieval_debug" not in st.session_state:
    st.session_state["retrieval_debug"] = {}
if "answer_result" not in st.session_state:
    st.session_state["answer_result"] = None
if "answer_debug" not in st.session_state:
    st.session_state["answer_debug"] = {}

left_col, right_col = st.columns([1, 1])

if search_clicked:
    with st.spinner("正在检索文档..."):
        try:
            results, debug_info = service.search(
                dataset_path=dataset_path,
                query=query,
                company_name=company_name,
                top_n=top_n,
                llm_reranking=llm_reranking,
                llm_reranking_sample_size=llm_reranking_sample_size,
                return_parent_pages=return_parent_pages,
            )
            st.session_state["retrieval_results"] = results
            st.session_state["retrieval_debug"] = debug_info
            st.success(f"检索完成，共返回 {len(results)} 条结果。")
        except Exception as err:
            st.error(f"检索失败：{err}")

if answer_clicked:
    if not st.session_state["retrieval_results"]:
        st.warning("请先执行“检索文档”。")
    else:
        with st.spinner("正在生成答案..."):
            try:
                answer, answer_debug = service.answer(
                    query=query,
                    schema=schema,
                    retrieval_results=st.session_state["retrieval_results"],
                    api_provider=api_provider,
                    answering_model=answering_model,
                )
                st.session_state["answer_result"] = answer
                st.session_state["answer_debug"] = answer_debug
                st.success("答案生成完成。")
            except Exception as err:
                st.error(f"答案生成失败：{err}")

with left_col:
    st.subheader("📄 检索结果")
    results = st.session_state["retrieval_results"]
    if not results:
        st.info("暂无检索结果。")
    else:
        for idx, item in enumerate(results, start=1):
            with st.expander(f"结果 {idx} | 页码: {item.get('page')} | 分数: {item.get('distance')}", expanded=(idx <= 3)):
                st.write(f"**来源**: {item.get('report') or item.get('company_name') or '未知'}")
                st.write(item.get("text", ""))

with right_col:
    st.subheader("🧾 答案结果")
    answer = st.session_state["answer_result"]
    if not answer:
        st.info("暂无答案。")
    else:
        st.markdown("### 最终答案")
        st.write(answer.get("final_answer", "N/A"))

        st.markdown("### 推理摘要")
        st.write(answer.get("reasoning_summary", ""))

        st.markdown("### 相关页码")
        st.write(answer.get("relevant_pages", []))

st.divider()
with st.expander("🛠 调试信息面板", expanded=False):
    st.markdown("#### 检索调试信息")
    st.json(st.session_state["retrieval_debug"])

    st.markdown("#### 答案调试信息")
    st.json(st.session_state["answer_debug"])

    st.markdown("#### 检索结果原始JSON")
    st.code(json.dumps(st.session_state["retrieval_results"], ensure_ascii=False, indent=2), language="json")
# add end

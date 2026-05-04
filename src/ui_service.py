from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time
import json

from src.retrieval import VectorRetriever, HybridRetriever
from src.api_requests import APIProcessor


# add by gq [2026-05-04：新增UI服务层，统一封装多数据集检索与问答逻辑]
class RAGUIService:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).resolve().parents[1]
        self.data_root = self.project_root / "data"

    def discover_datasets(self) -> Dict[str, Path]:
        datasets: Dict[str, Path] = {}
        if not self.data_root.exists():
            return datasets

        for path in sorted(self.data_root.iterdir()):
            if not path.is_dir():
                continue
            has_questions = (path / "questions.json").exists()
            has_chunks = (path / "databases" / "chunked_reports").exists()
            has_vectors = (path / "databases" / "vector_dbs").exists()
            if has_questions and has_chunks and has_vectors:
                datasets[path.name] = path
        return datasets

    def list_companies(self, dataset_path: Path) -> List[str]:
        docs_dir = dataset_path / "databases" / "chunked_reports"
        companies = set()
        for report_path in docs_dir.glob("*.json"):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                company_name = report.get("metainfo", {}).get("company_name")
                if company_name:
                    companies.add(company_name)
            except Exception:
                continue
        return sorted(companies)

    def _build_retriever(self, dataset_path: Path, llm_reranking: bool):
        vector_db_dir = dataset_path / "databases" / "vector_dbs"
        documents_dir = dataset_path / "databases" / "chunked_reports"
        if llm_reranking:
            return HybridRetriever(vector_db_dir=vector_db_dir, documents_dir=documents_dir)
        return VectorRetriever(vector_db_dir=vector_db_dir, documents_dir=documents_dir)

    def search(
        self,
        dataset_path: Path,
        query: str,
        company_name: Optional[str],
        top_n: int = 10,
        llm_reranking: bool = True,
        llm_reranking_sample_size: int = 20,
        return_parent_pages: bool = False,
    ) -> Tuple[List[dict], dict]:
        retriever = self._build_retriever(dataset_path, llm_reranking)
        started = time.perf_counter()

        if company_name:
            results = retriever.retrieve_by_company_name(
                company_name=company_name,
                query=query,
                top_n=top_n,
                llm_reranking_sample_size=llm_reranking_sample_size,
                return_parent_pages=return_parent_pages,
            )
        else:
            if hasattr(retriever, "retrieve_by_query"):
                results = retriever.retrieve_by_query(
                    query=query,
                    top_n=top_n,
                    llm_reranking_sample_size=llm_reranking_sample_size,
                    return_parent_pages=return_parent_pages,
                )
            else:
                results = []

        elapsed = round(time.perf_counter() - started, 3)
        debug_info = {
            "elapsed_seconds": elapsed,
            "dataset": dataset_path.name,
            "company_name": company_name,
            "top_n": top_n,
            "llm_reranking": llm_reranking,
            "llm_reranking_sample_size": llm_reranking_sample_size,
            "return_parent_pages": return_parent_pages,
            "result_count": len(results),
        }
        return results, debug_info

    @staticmethod
    def _format_rag_context(results: List[dict]) -> str:
        parts = []
        for r in results:
            page = r.get("page")
            report = r.get("report") or r.get("company_name")
            source = f" from {report}" if report else ""
            text = r.get("text", "")
            parts.append(f'Text retrieved{source} from page {page}:\n"""\n{text}\n"""')
        return "\n\n---\n\n".join(parts)

    def answer(
        self,
        query: str,
        schema: str,
        retrieval_results: List[dict],
        api_provider: str,
        answering_model: str,
    ) -> Tuple[dict, dict]:
        started = time.perf_counter()
        rag_context = self._format_rag_context(retrieval_results)

        processor = APIProcessor(provider=api_provider)
        answer = processor.get_answer_from_rag_context(
            question=query,
            rag_context=rag_context,
            schema=schema,
            model=answering_model,
        )
        elapsed = round(time.perf_counter() - started, 3)
        debug_info = {
            "elapsed_seconds": elapsed,
            "api_provider": api_provider,
            "answering_model": answering_model,
            "schema": schema,
            "response_data": getattr(processor, "response_data", None),
        }
        return answer, debug_info
# add end

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
import time
import hashlib
import zipfile

import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


# modified by gq [2026-05-04：根据MinerU官方文档重构，支持本地文件批量上传]
def _authorization_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """构建Authorization请求头"""
    token = api_key or os.getenv("MINERU_API_KEY")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _extract_text_from_block(block: Dict[str, Any]) -> str:
    # add by gq [2026-05-04：将MinerU content_list块转换为纯文本]
    content = block.get("content", {})
    if not isinstance(content, dict):
        return ""

    pieces: List[str] = []

    # 处理 paragraph / title 等结构
    paragraph_items = content.get("paragraph_content", [])
    if isinstance(paragraph_items, list):
        for item in paragraph_items:
            if isinstance(item, dict):
                text = item.get("content", "")
                if isinstance(text, str) and text.strip():
                    pieces.append(text.strip())

    # 处理 table / caption / 其它可能文本字段
    for key in ["text", "caption", "table_caption", "title", "content"]:
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            pieces.append(value.strip())

    # 去重保序
    seen = set()
    deduped: List[str] = []
    for p in pieces:
        if p not in seen:
            deduped.append(p)
            seen.add(p)

    return "\n".join(deduped).strip()
    # add end


def _normalize_mineru_zip_to_pipeline_json(zip_path: Path, output_json_path: Path, original_pdf_name: str) -> None:
    # add by gq [2026-05-04：将MinerU zip结果转换为pipeline可消费的01_parsed_reports JSON]
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

        content_list_name = ""
        if "content_list_v2.json" in names:
            content_list_name = "content_list_v2.json"
        else:
            matches = [n for n in names if n.endswith("content_list.json")]
            if matches:
                content_list_name = matches[0]

        if not content_list_name:
            raise ValueError(f"No content_list json found in MinerU zip: {zip_path}")

        raw = json.loads(zf.read(content_list_name).decode("utf-8", errors="ignore"))

    # raw 通常是: List[PageBlocks]，其中 PageBlocks 是 List[Block]
    pages = []
    total_text_blocks = 0
    total_tables = 0
    total_pictures = 0

    for page_index, page_blocks in enumerate(raw, start=1):
        normalized_blocks = []

        if isinstance(page_blocks, list):
            for b_idx, block in enumerate(page_blocks):
                if not isinstance(block, dict):
                    continue

                b_type = str(block.get("type", "text")).lower().strip()
                text = _extract_text_from_block(block)

                mapped_type = "text"
                if "table" in b_type:
                    mapped_type = "table"
                    total_tables += 1
                elif "image" in b_type or "figure" in b_type or "picture" in b_type:
                    mapped_type = "picture"
                    total_pictures += 1
                elif "title" in b_type or "header" in b_type:
                    mapped_type = "section_header"
                elif "list" in b_type:
                    mapped_type = "list_item"
                elif "caption" in b_type:
                    mapped_type = "caption"

                if mapped_type in {"text", "section_header", "list_item", "caption"} and text:
                    normalized_blocks.append({
                        "text": text,
                        "type": mapped_type,
                        "text_id": b_idx
                    })
                    total_text_blocks += 1
                elif mapped_type == "table":
                    normalized_blocks.append({
                        "text": text or "[TABLE]",
                        "type": "table",
                        "text_id": b_idx
                    })
                elif mapped_type == "picture":
                    normalized_blocks.append({
                        "type": "picture",
                        "picture_id": b_idx
                    })

        pages.append({
            "page": page_index,
            "content": normalized_blocks
        })

    sha1_name = hashlib.sha1(original_pdf_name.encode("utf-8")).hexdigest()
    output_data = {
        "metainfo": {
            "sha1_name": sha1_name,
            "pages_amount": len(pages),
            "text_blocks_amount": total_text_blocks,
            "tables_amount": total_tables,
            "pictures_amount": total_pictures,
            "equations_amount": 0,
            "footnotes_amount": 0,
            "company_name": Path(original_pdf_name).stem
        },
        "content": pages
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    # add end


def get_task_id(file_name: str, submit_url: Optional[str] = None, **kwargs) -> str:
    """提交PDF到MinerU解析服务并返回任务ID。

    使用MinerU批量文件上传接口：
    1. 申请上传链接
    2. PUT上传文件
    3. 系统自动提交解析任务

    环境变量：
    - MINERU_API_KEY：Bearer Token（必需）
    - MINERU_SUBMIT_URL：默认 https://mineru.net/api/v4/file-urls/batch
    """
    pdf_path = Path(file_name)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    target_url = submit_url or os.getenv("MINERU_SUBMIT_URL", "https://mineru.net/api/v4/file-urls/batch")

    data = {
        "files": [{"name": pdf_path.name}],
        "model_version": "vlm"
    }

    headers = _authorization_headers()
    headers["Content-Type"] = "application/json"

    response = requests.post(target_url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()

    if result.get("code") != 0:
        raise ValueError(f"MinerU API error: {result.get('msg', 'Unknown error')}")

    batch_id = result["data"]["batch_id"]
    file_url = result["data"]["file_urls"][0]

    with pdf_path.open("rb") as f:
        upload_response = requests.put(file_url, data=f, timeout=120)
        upload_response.raise_for_status()

    print(f"File uploaded successfully: {pdf_path.name}, batch_id: {batch_id}")
    return batch_id


def get_result(task_id: str, result_url_template: Optional[str] = None, output_path: Optional[str] = None, max_retries: int = 60, retry_interval: int = 10) -> Dict[str, Any]:
    """获取MinerU解析结果，轮询直到完成。"""
    template = result_url_template or os.getenv("MINERU_RESULT_URL_TEMPLATE", "https://mineru.net/api/v4/extract-results/batch/{task_id}")
    url = template.format(task_id=task_id)

    headers = _authorization_headers()

    for attempt in range(max_retries):
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("code") != 0:
            raise ValueError(f"MinerU API error: {result.get('msg', 'Unknown error')}")

        extract_results = result["data"]["extract_result"]

        all_done = True
        for file_result in extract_results:
            state = file_result["state"]
            file_name = file_result.get("file_name", "unknown")

            if state == "failed":
                err_msg = file_result.get("err_msg", "Unknown error")
                raise ValueError(f"File {file_name} parsing failed: {err_msg}")
            elif state in ["waiting-file", "pending", "running", "converting"]:
                all_done = False
                print(f"[{attempt+1}/{max_retries}] {file_name}: {state}")

        if all_done:
            print("All files parsed successfully!")

            if output_path and extract_results:
                first_result = extract_results[0]
                if "full_zip_url" in first_result:
                    zip_url = first_result["full_zip_url"]
                    zip_response = requests.get(zip_url, timeout=120)
                    zip_response.raise_for_status()

                    target_path = Path(output_path)
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # modified by gq [2026-05-04：保留zip并额外产出pipeline兼容json]
                    zip_path = target_path.with_suffix('.zip')
                    with zip_path.open("wb") as f:
                        f.write(zip_response.content)

                    _normalize_mineru_zip_to_pipeline_json(
                        zip_path=zip_path,
                        output_json_path=target_path,
                        original_pdf_name=first_result.get("file_name", target_path.stem)
                    )

                    print(f"Result saved to: {zip_path}")
                    print(f"Normalized JSON saved to: {target_path}")
                    # mod end

            return result

        time.sleep(retry_interval)

    raise TimeoutError(f"Parsing timeout after {max_retries * retry_interval} seconds")
# mod end

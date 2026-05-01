import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests


# add by gq [2026-04-30：封装MinerU解析任务提交和结果获取]
def _authorization_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    token = api_key or os.getenv("MINERU_API_KEY")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _extract_task_id(response_data: Dict[str, Any]) -> str:
    candidates = [
        response_data.get("task_id"),
        response_data.get("id"),
        response_data.get("data", {}).get("task_id") if isinstance(response_data.get("data"), dict) else None,
        response_data.get("data", {}).get("id") if isinstance(response_data.get("data"), dict) else None,
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    raise ValueError(f"MinerU response does not contain task_id: {response_data}")


def get_task_id(file_name: str, submit_url: Optional[str] = None, file_field: Optional[str] = None) -> str:
    """提交PDF到MinerU解析服务并返回任务ID。

    环境变量：
    - MINERU_SUBMIT_URL：MinerU任务提交接口
    - MINERU_API_KEY：可选Bearer Token
    - MINERU_FILE_FIELD：上传字段名，默认file
    """
    pdf_path = Path(file_name)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    target_url = submit_url or os.getenv("MINERU_SUBMIT_URL")
    if not target_url:
        raise ValueError("MINERU_SUBMIT_URL is required to submit MinerU tasks")

    upload_field = file_field or os.getenv("MINERU_FILE_FIELD", "file")
    with pdf_path.open("rb") as file_obj:
        files = {upload_field: (pdf_path.name, file_obj, "application/pdf")}
        response = requests.post(target_url, headers=_authorization_headers(), files=files, timeout=120)
    response.raise_for_status()
    return _extract_task_id(response.json())


def get_result(task_id: str, result_url_template: Optional[str] = None, output_path: Optional[str] = None) -> Dict[str, Any]:
    """获取MinerU解析结果，可选保存为JSON文件。

    环境变量：
    - MINERU_RESULT_URL_TEMPLATE：结果查询接口模板，例如 https://example.com/tasks/{task_id}
    - MINERU_API_KEY：可选Bearer Token
    """
    template = result_url_template or os.getenv("MINERU_RESULT_URL_TEMPLATE")
    if not template:
        raise ValueError("MINERU_RESULT_URL_TEMPLATE is required to fetch MinerU results")

    response = requests.get(template.format(task_id=task_id), headers=_authorization_headers(), timeout=120)
    response.raise_for_status()
    result = response.json()

    if output_path:
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("w", encoding="utf-8") as file_obj:
            json.dump(result, file_obj, ensure_ascii=False, indent=2)

    return result
# add end

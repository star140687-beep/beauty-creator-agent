import json
import os

import httpx
import streamlit as st

from beauty_creator_agent.services.documents import DocumentExtractionError, extract_reference

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
TERMINAL_STATUSES = {"awaiting_human_review", "completed", "rejected", "failed"}

st.set_page_config(page_title="Beauty Creator Agent", layout="wide")
st.title("Beauty Creator Agent")

with st.form("create-task"):
    uploaded_file = st.file_uploader("上传需求或产品资料（PDF、DOCX、TXT、MD；最大 10 MB）")
    upload_role = st.selectbox(
        "文件用途",
        options=["brief", "product_material", "existing_content"],
        format_func={
            "brief": "内容需求 Brief（只影响写作要求）",
            "product_material": "产品资料（作为待核验材料）",
            "existing_content": "已有文案（用于改写参考）",
        }.get,
    )
    brand = st.text_input("品牌")
    product = st.text_input("产品名称")
    market = st.selectbox("投放市场", ["CN", "US", "EU"], index=0)
    description = st.text_area("产品描述")
    objective = st.text_input("目标", value="生成自然、不夸张的小红书种草文案")
    audience = st.text_input("目标人群")
    target_length = st.slider("正文目标长度（中文字符）", 200, 5000, 800, step=100)
    submitted = st.form_submit_button("开始生成")

if submitted:
    uploaded_references: list[dict[str, object]] = []
    if uploaded_file is not None:
        try:
            reference = extract_reference(
                filename=uploaded_file.name,
                data=uploaded_file.getvalue(),
                role=upload_role,
            )
            uploaded_references.append(reference.model_dump())
        except DocumentExtractionError as exc:
            st.error(f"无法读取上传文件：{exc}")
            st.stop()
    payload = {
        "product": {"brand": brand or None, "name": product, "description": description or None},
        "platform": "xiaohongshu",
        "market": market,
        "objective": objective,
        "audience": audience or None,
        "target_length": target_length,
        "uploaded_references": uploaded_references,
    }
    try:
        response = httpx.post(f"{API_URL}/v1/tasks", json=payload, timeout=30)
        response.raise_for_status()
        st.session_state.task_id = response.json()["task_id"]
    except httpx.HTTPError as exc:
        st.error(f"无法创建任务：{exc}")


@st.fragment(run_every=2)
def task_panel(task_id: str) -> None:
    """Poll task status so long local model calls remain visible to the user."""
    try:
        response = httpx.get(f"{API_URL}/v1/tasks/{task_id}", timeout=30)
        response.raise_for_status()
        task = response.json()
    except httpx.HTTPError as exc:
        st.error(f"无法读取任务状态：{exc}")
        return

    status = task["status"]
    st.info(f"任务 ID：{task_id}")
    st.subheader(f"状态：{status}")
    if status not in TERMINAL_STATUSES:
        st.caption("正在执行工作流，页面会每 2 秒自动更新。")
    state = task.get("state", {})
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Evidence")
        st.json(state.get("evidence", []))
    with col2:
        st.subheader("Compliance")
        st.json(state.get("compliance_result", {}))
    if state.get("current_draft"):
        draft = state["current_draft"]
        st.subheader(draft["title"])
        st.text_area("正文", value=draft["body"], height=300, disabled=True)
        if draft.get("warnings"):
            st.warning("\n".join(draft["warnings"]))
        if status == "awaiting_human_review":
            action = st.radio("审核操作", ["approve", "reject"], horizontal=True)
            feedback = st.text_input("审核意见")
            if st.button("提交审核"):
                try:
                    result = httpx.post(
                        f"{API_URL}/v1/tasks/{task_id}/review",
                        json={"action": action, "feedback": feedback or None},
                        timeout=180,
                    )
                    result.raise_for_status()
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(f"无法提交审核：{exc}")
    with st.expander("Workflow events"):
        st.code(json.dumps(task.get("events", []), ensure_ascii=False, indent=2))


task_id = st.session_state.get("task_id")
if task_id:
    task_panel(task_id)

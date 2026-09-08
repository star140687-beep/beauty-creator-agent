import json
import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Beauty Creator Agent", layout="wide")
st.title("Beauty Creator Agent")

with st.form("create-task"):
    brand = st.text_input("品牌")
    product = st.text_input("产品名称")
    description = st.text_area("产品描述")
    objective = st.text_input("目标", value="生成自然、不夸张的小红书种草文案")
    audience = st.text_input("目标人群")
    submitted = st.form_submit_button("开始生成")

if submitted:
    payload = {
        "product": {"brand": brand or None, "name": product, "description": description or None},
        "platform": "xiaohongshu",
        "objective": objective,
        "audience": audience or None,
    }
    response = httpx.post(f"{API_URL}/v1/tasks", json=payload, timeout=30)
    response.raise_for_status()
    st.session_state.task_id = response.json()["task_id"]

task_id = st.session_state.get("task_id")
if task_id:
    st.info(f"Task ID: {task_id}")
    if st.button("刷新状态"):
        st.rerun()
    task = httpx.get(f"{API_URL}/v1/tasks/{task_id}", timeout=30).json()
    st.subheader(f"状态：{task['status']}")
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
        edited_body = st.text_area("正文", value=draft["body"], height=300)
        if task["status"] == "awaiting_human_review":
            action = st.radio("审核操作", ["approve", "edit", "reject"], horizontal=True)
            feedback = st.text_input("审核意见")
            if st.button("提交审核"):
                review = {"action": action, "feedback": feedback or None}
                if action == "edit":
                    review["body"] = edited_body
                result = httpx.post(
                    f"{API_URL}/v1/tasks/{task_id}/review", json=review, timeout=180
                )
                result.raise_for_status()
                st.json(result.json())
    with st.expander("Workflow events"):
        st.code(json.dumps(task.get("events", []), ensure_ascii=False, indent=2))

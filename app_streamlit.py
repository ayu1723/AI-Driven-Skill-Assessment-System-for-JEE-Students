import streamlit as st
import json
import os
from datetime import datetime
from soca_generator import analyze_responses, load_questionnaire

RESULTS_FILE = "results.json"

# ---------- Helper: Save results ----------
def save_result_to_file(student_name, student_class, analysis):
    result_data = {
        "student": student_name,
        "class": student_class,
        "timestamp": datetime.now().isoformat(),
        "score_obtained": analysis["score_obtained"],
        "total_weight": analysis["total_weight"],
        "percent_score": analysis["percent_score"],
        "details": analysis["details"]
    }
    all_results = load_past_results()
    all_results.append(result_data)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4)

# ---------- Helper: Load results ----------
def load_past_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# ---------- Helper: Save updated results ----------
def save_results(results_list):
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results_list, f, indent=4)

# ---------- Helper: Get question map ----------
def get_question_map(q_path):
    q_data = load_questionnaire(q_path)
    return {q["id"]: q["prompt"] for q in q_data["questions"]}

# ---------- Streamlit Navigation ----------
st.set_page_config(page_title="JEE SOCA Assessment", layout="centered")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Take Assessment", "View Past Records", "Manage Records"])

# ---------- Page 1: Take Assessment ----------
if page == "Take Assessment":
    st.title("JEE SOCA Assessment (Prototype)")

    # Student info
    st.sidebar.header("Student Info")
    name = st.sidebar.text_input("Name", value="Student")
    grade = st.sidebar.selectbox("Class", ["11", "12", "Dropper", "Other"])

    # Load questionnaire based on grade
    questionnaire_file = {
        "11": "questionnaire_11.json",
        "12": "questionnaire_12.json",
        "Dropper": "questionnaire_dropper.json",
        "Other": "questionnaire_other.json"
    }[grade]
    q = load_questionnaire(questionnaire_file)

    # Questionnaire form
    st.header("Questionnaire")
    responses = {}
    for ques in q["questions"]:
        qid = ques["id"]
        st.markdown(f"**{ques['prompt']}**")
        if ques["type"] == "mcq":
            opts = ques["options"]
            choice = st.radio("", opts, key=qid)
            try:
                idx = opts.index(choice)
            except:
                idx = choice
            responses[qid] = idx
        elif ques["type"] == "scale":
            v = st.slider("", min_value=ques.get("min", 1), max_value=ques.get("max", 5),
                          value=(ques.get("min", 1) + ques.get("max", 5)) // 2, key=qid)
            responses[qid] = v
        elif ques["type"] == "short":
            txt = st.text_area("", value="", key=qid, height=100)
            responses[qid] = txt
        st.write("---")

    if st.button("Generate SOCA Report"):
        with st.spinner("Analyzing responses... (this may take a minute)"):
            report = analyze_responses(
                responses,
                questionnaire_path=questionnaire_file,
                student_meta={"name": name, "grade": grade}
            )
            save_result_to_file(name, grade, report["analysis_summary"])
            st.success("SOCA report generated")

            # Display SOCA Analysis in tabs
            st.subheader("SOCA Analysis Reports")
            tabs = st.tabs(["Student View", "Educator View"])
            with tabs[0]:
                st.markdown(report["student_report"])
            with tabs[1]:
                st.markdown(report["educator_report"])

            # Marks Summary
            st.subheader("Marks Summary")
            details = report["analysis_summary"]["details"]
            marks_table = []
            for qid, data in details.items():
                result = data.get("result", None)
                if result is not None:
                    marks = data.get("weight", 0)
                    q_text = get_question_map(questionnaire_file)[qid]
                    marks_table.append({
                        "Question": q_text,
                        "Result": "✅ Correct" if result == "correct" else "❌ Wrong",
                        "Marks": marks
                    })
            if marks_table:
                st.table(marks_table)
            st.write(f"**Total Marks:** {report['analysis_summary']['score_obtained']} / {report['analysis_summary']['total_weight']}")
            st.write(f"**Percentage:** {report['analysis_summary']['percent_score']}%")

# ---------- Page 2: View Past Records ----------
elif page == "View Past Records":
    st.title("Past Assessment Records")
    results = load_past_results()
    if not results:
        st.info("No past records found yet.")
    else:
        for record in results:
            record_class = record.get("class", "Other")
            q_file = {
                "11": "questionnaire_11.json",
                "12": "questionnaire_12.json",
                "Dropper": "questionnaire_dropper.json",
                "Other": "questionnaire_other.json"
            }[record_class]
            q_map = get_question_map(q_file)
            with st.expander(f"{record['student']} ({record_class}) — {record['timestamp']}  |  Score: {record['score_obtained']}/{record['total_weight']} ({record['percent_score']}%)"):
                breakdown_table = []
                for qid, data in record["details"].items():
                    result = data.get("result", None)
                    if result is not None:
                        breakdown_table.append({
                            "Question": q_map.get(qid, qid),
                            "Result": "✅ Correct" if result == "correct" else "❌ Wrong",
                            "Marks": data.get("weight", 0)
                        })
                if breakdown_table:
                    st.table(breakdown_table)

# ---------- Page 3: Manage Records ----------
elif page == "Manage Records":
    st.title("Manage Records")
    results = load_past_results()
    if not results:
        st.info("No records to manage.")
    else:
        if st.button("Delete ALL Records"):
            save_results([])
            st.warning("All records deleted.")

        student_names = list(set(r["student"] for r in results))
        selected_student = st.selectbox("Delete records for a specific student:", ["None"] + student_names)
        if selected_student != "None":
            if st.button(f"Delete records for {selected_student}"):
                results = [r for r in results if r["student"] != selected_student]
                save_results(results)
                st.success(f"Deleted all records for {selected_student}.")

        date_cutoff = st.date_input("Delete records before date (YYYY-MM-DD):")
        if st.button("Delete records before this date"):
            cutoff_dt = datetime.combine(date_cutoff, datetime.min.time())
            results = [r for r in results if datetime.fromisoformat(r["timestamp"]) >= cutoff_dt]
            save_results(results)
            st.success(f"Deleted records before {date_cutoff}.")

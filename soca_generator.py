import json
from typing import Dict, Any
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

MODEL_NAME = "google/flan-t5-base"

# Load model
_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
text2text = pipeline("text2text-generation", model=_model, tokenizer=_tokenizer, device=-1)

# Load questionnaire
def load_questionnaire(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Simple scoring
def score_responses(questionnaire: Dict[str, Any], responses: Dict[str, Any]) -> Dict[str, Any]:
    total_weight = 0
    score_obtained = 0
    short_answers = {}
    details = {}

    for q in questionnaire["questions"]:
        qid = q["id"]
        qtype = q["type"]
        weight = q.get("weight", 1)
        total_weight += weight
        ans = responses.get(qid, None)

        if qtype == "mcq" and "answer_key" in q:
            try:
                idx = int(ans) if isinstance(ans, int) else q["options"].index(ans)
            except:
                idx = None
            if idx == q["answer_key"]:
                score_obtained += weight
                details[qid] = {"result": "correct", "weight": weight}
            else:
                details[qid] = {"result": "incorrect", "weight": 0}
        elif qtype == "scale":
            try:
                val = float(ans)
            except:
                val = 0
            norm = (val - q.get("min", 1)) / (q.get("max", 5) - q.get("min", 1))
            score_obtained += norm * weight
            details[qid] = {"value": val, "normalized": norm}
        elif qtype == "short":
            short_answers[qid] = ans
            details[qid] = {"value": ans}
        else:
            details[qid] = {"value": ans}

    percent = (score_obtained / total_weight) * 100 if total_weight else 0
    return {
        "total_weight": total_weight,
        "score_obtained": score_obtained,
        "percent_score": percent,
        "short_answers": short_answers,
        "details": details
    }

# Strict SOCA format prompts
def build_prompt_student(analysis: Dict[str, Any]) -> str:
    return f"""
You are a friendly mentor for JEE students.
Based on the student's performance data below, create a SOCA (Strengths, Opportunities, Challenges, Action Plan) report.
MUST follow this exact structure with headings and bullet points:

Strengths:
- Point 1
- Point 2

Opportunities:
- Point 1
- Point 2

Challenges:
- Point 1
- Point 2

Action Plan:
1. Step 1
2. Step 2
3. Step 3

Focus on encouragement and practical improvement tips.

Data:
Score: {analysis['score_obtained']} / {analysis['total_weight']} ({analysis['percent_score']:.1f}%)
Short Answers: {json.dumps(analysis['short_answers'], indent=2)}
"""

def build_prompt_educator(analysis: Dict[str, Any]) -> str:
    return f"""
You are an academic advisor analyzing a JEE student's preparation.
Based on the student's performance data below, create a detailed SOCA (Strengths, Opportunities, Challenges, Action Plan) report.
MUST follow this exact structure with headings and bullet points:

Strengths:
- Point 1
- Point 2

Opportunities:
- Point 1
- Point 2

Challenges:
- Point 1
- Point 2

Action Plan:
1. Step 1
2. Step 2
3. Step 3

Highlight academic trends, knowledge gaps, and professional recommendations.

Data:
Score: {analysis['score_obtained']} / {analysis['total_weight']} ({analysis['percent_score']:.1f}%)
Full response details: {json.dumps(analysis['details'], indent=2)}
"""

# LLM call
def generate_text(prompt: str) -> str:
    res = text2text(prompt, max_new_tokens=300, num_return_sequences=1)
    return res[0]["generated_text"]

# Main function
def analyze_responses(responses: Dict[str, Any], questionnaire_path: str, student_meta: Dict[str, Any] = None) -> Dict[str, Any]:
    q = load_questionnaire(questionnaire_path)
    analysis = score_responses(q, responses)

    prompt_student = build_prompt_student(analysis)
    prompt_educator = build_prompt_educator(analysis)

    student_report = generate_text(prompt_student)
    educator_report = generate_text(prompt_educator)

    return {
        "analysis_summary": analysis,
        "student_report": student_report,
        "educator_report": educator_report
    }

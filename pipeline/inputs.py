"""Rules for what a person must give before a practice can start, shared by every route that starts one.

The word count has a twin in the browser (src/jobWords.js). Both read tests/fixtures/word_count_cases.json, so a
description that passes in the form cannot be refused by the server.
"""
import re

MIN_JD_WORDS = 20

# A word is a run of letters or digits, with apostrophes, hyphens and dots kept inside it (don't, e-mail, 3.5). Chinese,
# Japanese and Korean have no spaces, so two characters count as one word.
_LATIN = re.compile(r"[A-Za-z0-9À-ɏ]+(?:['’.\-][A-Za-z0-9À-ɏ]+)*")
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")


def count_words(text):
    text = text or ""
    return len(_LATIN.findall(text)) + (len(_CJK.findall(text)) + 1) // 2


def job_too_short(text):
    """The message to show when the job description is too short to aim questions at, or None when it is long enough."""
    n = count_words(text)
    if n >= MIN_JD_WORDS:
        return None
    return (f"The job description is only {n} word{'' if n == 1 else 's'}. The interviewer aims its questions at it, "
            f"so a short one gives generic questions. Paste the responsibilities and requirements, at least {MIN_JD_WORDS} words.")


# What each level means for the questions. Anything not in this table is ignored, so the value cannot carry text
# into the interviewer's instructions.
AGE_GROUPS = {
    "middle_school": "a middle school student. Ask about school, clubs, hobbies and simple projects. Keep questions short and friendly",
    "high_school": "a high school student. Ask about classes, clubs, activities and projects. Do not expect work experience",
    "college": "a college student. Ask about coursework, projects, internships and campus roles",
    "early_career": "early in their career, with up to about three years of work. Ask about the work they own and what they learned",
    "mid_career": "in the middle of their career, with roughly four to ten years of work. Ask about scope, trade-offs and results",
    "senior_career": "a senior professional with over ten years of work. Ask about leadership, strategy and judgment calls",
}


def level_line(age_group):
    return AGE_GROUPS.get((age_group or "").strip())

import pytest

from src.tools.ask_student import AskStudentError, ask_student

QUESTION = "Quelle est ta note en SVT ?"


def test_ask_student_returns_needs_input_with_the_question():
    assert ask_student(QUESTION) == {"status": "needs_input", "question": QUESTION}


def test_ask_student_strips_surrounding_whitespace():
    assert ask_student(f"  {QUESTION}  ") == {"status": "needs_input", "question": QUESTION}


def test_ask_student_rejects_an_empty_question():
    with pytest.raises(AskStudentError, match="non-empty"):
        ask_student("   ")


def test_ask_student_rejects_two_questions_at_once():
    with pytest.raises(AskStudentError, match="one question"):
        ask_student("Quelle est ta série ? Et ta note en SVT ?")

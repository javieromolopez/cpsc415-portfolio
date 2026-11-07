"""No-key tests for the transcript checker (spec.md behaviors 8-10).

    python -m pytest voice/tests/test_check.py -v     # free, well under a second
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check import compare, wer, words

# Thirteen words, the shape of my own clips: a name and the course number.
# (The first draft had twelve; test_said_has_thirteen_words caught it.)
SAID = "Hi, I'm Javier Romo from CPSC 415 and I study data science here."


def test_said_has_thirteen_words():
    assert len(words(SAID)) == 13


def test_words_ignore_case_and_punctuation():
    assert words("Hello, World!  It's 415.") == ["hello", "world", "it's", "415"]


def test_curly_apostrophe_is_the_same_word():
    assert words("I’m") == words("I'm")


def test_perfect_transcript_scores_zero():
    assert wer(SAID, SAID) == 0.0
    assert wer(SAID, "hi i'm javier romo from cpsc 415 and i study data science here") == 0.0


def test_one_substitution_in_thirteen_words():
    got = SAID.replace("Javier", "Xavier")              # the likeliest thing a transcriber does to my name
    assert abs(wer(SAID, got) - 1 / 13) < 1e-9


def test_insertions_count_against_the_transcript():
    got = SAID + " Music"                               # Whisper's habit on trailing silence
    assert abs(wer(SAID, got) - 1 / 13) < 1e-9


def test_empty_transcript_is_a_failed_transcript_not_a_crash():
    assert wer(SAID, "") == 1.0
    assert wer(SAID, None) == 1.0
    result = compare(SAID, None)
    assert result["empty"] and not result["ok"]
    assert result["wer"] == 1.0


def test_whitespace_only_transcript_is_empty():
    assert compare(SAID, "   \n ")["empty"]


def test_name_that_must_survive_is_reported_even_within_tolerance():
    got = SAID.replace("Javier", "Xavier")              # 1/13 = 0.077, inside 0.15 on its own
    result = compare(SAID, got, must_contain=["Javier Romo", "415"], max_wer=0.15)
    assert result["missing"] == ["Javier Romo"]
    assert not result["ok"]


def test_small_drift_within_tolerance_is_ok():
    got = "Hi, I'm Javier Romo from CPSC 415 and I study data science."     # one word dropped
    result = compare(SAID, got, must_contain=["Javier Romo", "415"], max_wer=0.15)
    assert result["ok"]
    assert result["wer"] == round(1 / 13, 3)


def test_drift_beyond_tolerance_fails():
    got = "Hi, I'm Javier Romo from CPSC 415."                         # five words dropped
    result = compare(SAID, got, must_contain=["Javier Romo", "415"], max_wer=0.15)
    assert not result["ok"] and result["missing"] == []


def test_number_read_as_words_is_a_miss():
    got = SAID.replace("415", "four fifteen")
    assert compare(SAID, got, must_contain=["415"])["missing"] == ["415"]


def test_must_contain_ignores_spacing_and_case():
    got = "javierromo from cpsc415"
    assert compare("x", got, must_contain=["Javier Romo", "CPSC 415"], max_wer=9)["missing"] == []


def test_default_tolerance_is_the_spec_value():
    got = "Hi I'm Javier Romo from CPSC 415 and I study data."          # 2 of 13 = 0.154, just over 0.15
    assert not compare(SAID, got)["ok"]

import pytest

from backend.services import diff_service


@pytest.mark.parametrize(
    ("old_text", "new_text", "expected"),
    [
        ("Hello world.", "Hello brave world.", "Added 1 word."),
        ("The cat sat.", "The dog sat.", "Changed 1 word."),
        (
            "The old red car stopped.",
            "The new fast blue car stopped.",
            "Changed 2 words and added 1 word.",
        ),
        (
            "Hello world.",
            "Hello  world!",
            "Updated capitalization, punctuation, or formatting.",
        ),
        ("Real-time editing works.", "Editing works.", "Removed 1 word."),
        ("No changes", "No changes", "No content changes detected."),
    ],
)
def test_generate_stub_summary(old_text, new_text, expected):
    chunks = diff_service.build_diff(old_text, new_text)

    assert diff_service.generate_stub_summary(chunks) == expected

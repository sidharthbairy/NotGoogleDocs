import re
from difflib import SequenceMatcher


def tokenize_text(text):
    return re.findall(r"\S+\s*|\s+", text)


def build_diff(old_text, new_text):
    old_tokens = tokenize_text(old_text)
    new_tokens = tokenize_text(new_text)
    matcher = SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    chunks = []

    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        left = "".join(old_tokens[old_start:old_end])
        right = "".join(new_tokens[new_start:new_end])
        if not left and not right:
            continue
        chunks.append({"type": tag, "left": left, "right": right})

    return chunks


def word_count(text):
    return len(re.findall(r"\S+", text))


def format_word_count(count):
    label = "word" if count == 1 else "words"
    return f"{count} {label}"


def generate_stub_summary(chunks, is_initial_snapshot):
    if is_initial_snapshot:
        return "Initial snapshot saved."

    added = sum(word_count(chunk["right"]) for chunk in chunks if chunk["type"] in ("insert", "replace"))
    removed = sum(word_count(chunk["left"]) for chunk in chunks if chunk["type"] in ("delete", "replace"))

    if added == 0 and removed == 0:
        return "No content changes detected."
    if added and removed:
        return (
            "Stub summary: revised the document with "
            f"{format_word_count(added)} added and {format_word_count(removed)} removed."
        )
    if added:
        return f"Stub summary: expanded the document with {format_word_count(added)} added."
    return f"Stub summary: tightened the document with {format_word_count(removed)} removed."

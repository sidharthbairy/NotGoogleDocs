import re
from difflib import SequenceMatcher


WORD_PATTERN = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*", re.UNICODE)


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


def extract_words(text):
    return [word.casefold() for word in WORD_PATTERN.findall(text)]


def format_word_count(count):
    label = "word" if count == 1 else "words"
    return f"{count} {label}"


def generate_stub_summary(chunks):
    old_text = "".join(chunk["left"] for chunk in chunks)
    new_text = "".join(chunk["right"] for chunk in chunks)
    if old_text == new_text:
        return "No content changes detected."

    old_words = extract_words(old_text)
    new_words = extract_words(new_text)
    matcher = SequenceMatcher(a=old_words, b=new_words, autojunk=False)
    changed = 0
    added = 0
    removed = 0

    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        old_count = old_end - old_start
        new_count = new_end - new_start
        if tag == "insert":
            added += new_count
        elif tag == "delete":
            removed += old_count
        elif tag == "replace":
            changed += min(old_count, new_count)
            added += max(new_count - old_count, 0)
            removed += max(old_count - new_count, 0)

    descriptions = []
    if changed:
        descriptions.append(f"changed {format_word_count(changed)}")
    if added:
        descriptions.append(f"added {format_word_count(added)}")
    if removed:
        descriptions.append(f"removed {format_word_count(removed)}")

    if not descriptions:
        return "Updated capitalization, punctuation, or formatting."
    if len(descriptions) == 1:
        sentence = descriptions[0]
    elif len(descriptions) == 2:
        sentence = " and ".join(descriptions)
    else:
        sentence = f"{', '.join(descriptions[:-1])}, and {descriptions[-1]}"
    return f"{sentence.capitalize()}."

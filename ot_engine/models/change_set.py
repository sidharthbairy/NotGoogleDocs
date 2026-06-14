from dataclasses import dataclass
from ot_engine.models.operation import Retain, Insert, Delete, Op

from difflib import SequenceMatcher

@dataclass(frozen=True)
class ChangeSet:
    base_length: int
    target_length: int
    ops: tuple[Op, ...]

    def __post_init__(self):
        if self.base_length < 0:
            raise ValueError("base_length cannot be negative")
        
        if self.target_length < 0:
            raise ValueError("target_length cannot be negative")
        
        consumed = 0 
        produced = 0

        for op in self.ops:
            if isinstance(op, Retain):
                consumed += op.count
                produced += op.count
            elif isinstance(op, Insert):
                produced += op.length
            elif isinstance(op, Delete):
                consumed += op.count
            else:
                raise TypeError(f"Unknown operation: {op}")
        
        if consumed != self.base_length:
            raise ValueError(
                f"ChangeSet consumes {consumed} chars, "
                f"but base_length is {self.base_length}"
            )
        
        if produced != self.target_length:
            raise ValueError(
                f"ChangeSet produces {produced} chars, "
                f"but target_length is {self.target_length}"
            )
        
def changeset_to_dict(change_set):
    ops = []

    for op in change_set.ops:
        if isinstance(op, Retain):
            ops.append({
                "type": "retain",
                "count": op.count,
            })
        elif isinstance(op, Insert):
            ops.append({
                "type": "insert",
                "text": op.text,
            })
        elif isinstance(op, Delete):
            ops.append({
                "type": "delete",
                "count": op.count,
            })
    
    return {
        "baseLength": change_set.base_length,
        "targetLength": change_set.target_length,
        "ops": ops
    }
        
def changeset_from_dict(data):
    from ot_engine.utils.constructors import changeset

    ops = []

    for op in data["ops"]:
        if op["type"] == "retain":
            ops.append(Retain(op["count"]))
        elif op["type"] == "insert":
            ops.append(Insert(op["text"]))
        elif op["type"] == "delete":
            ops.append(Delete(op["count"]))
        else:
            raise ValueError(f"Unknown op type: {op['type']}")

    return changeset(
        base_length=data["baseLength"],
        ops=ops,
    )

def text_to_changeset(old_text: str, new_text: str):
    from ot_engine.utils.constructors import changeset, delete, insert, retain

    if old_text == new_text:
        if len(old_text) == 0:
            return changeset(base_length=0, ops=[])
        return changeset(base_length=len(old_text), ops=[retain(len(old_text))])
    
    matcher = SequenceMatcher(a=old_text, b=new_text, autojunk=False)
    ops: list[Op] = []

    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            count = old_end - old_start
            if count > 0:
                ops.append(retain(count))
        elif tag == "insert":
            text = new_text[new_start: new_end]
            if text:
                ops.append(insert(text))
        elif tag == "delete":
            count = old_end - old_start
            if count > 0:
                ops.append(delete(count))
        elif tag == "replace":
            delete_count = old_end - old_start
            insert_text = new_text[new_start: new_end]
            if delete_count > 0:
                ops.append(delete(delete_count))
            if insert_text:
                ops.append(insert(insert_text))
    
    if not ops:
        return changeset(base_length=len(old_text), ops=[retain(len(old_text))])
    return changeset(base_length=len(old_text), ops=ops)

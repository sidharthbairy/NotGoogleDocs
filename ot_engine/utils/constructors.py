from ot_engine.models.operation import *
from ot_engine.models.change_set import ChangeSet

def retain(count: int) -> Retain:
    return Retain(count)

def insert(text: str) -> Insert:
    return Insert(text)

def delete(count: int) -> Delete:
    return Delete(count)

def changeset(base_length: int, ops: list[Op]) -> ChangeSet:
    normalized_ops = normalize_ops(ops)

    consumed = 0
    produced = 0 

    for op in normalized_ops:
        if isinstance(op, Retain):
            consumed += op.count
            produced += op.count
        elif isinstance(op, Insert):
            produced += op.length
        elif isinstance(op, Delete):
            consumed += op.count
    
    if consumed != base_length:
        raise ValueError(
            f"Ops consume {consumed} chars, but base_length is {base_length}"
        )
    
    return ChangeSet(
        base_length=base_length,
        target_length=produced,
        ops=tuple(normalized_ops)
    )

# Function to skip empty lists and preprocess edge cases for two of the same operations
def normalize_ops(ops: list[Op]) -> list[Op]:
    result: list[Op] = []

    for op in ops:
        if isinstance(op, Retain) and op.count == 0:
            continue
        if isinstance(op, Insert) and op.text == "":
            continue
        if isinstance(op, Delete) and op.count == 0:
            continue

        if not result:
            result.append(op)
            continue
            
        last = result[-1]

        if isinstance(last, Retain) and isinstance(op, Retain):
            result[-1] = Retain(last.count + op.count)

        elif isinstance(last, Delete) and isinstance(op, Delete):
            result[-1] = Delete(last.count + op.count)

        elif isinstance(last, Insert) and isinstance(op, Insert):
            result[-1] = Insert(last.text + op.text)

        else:
            result.append(op)
        
    return result
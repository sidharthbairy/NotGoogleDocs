from ot_engine.models.change_set import ChangeSet
from ot_engine.models.operation import *
from ot_engine.utils.constructors import *

def apply_changeset(document: str, cs: ChangeSet) -> str:
    if len(document) != cs.base_length:
        raise ValueError(
            f"Document length {len(document)} does not match "
            f"changeset base_length {cs.base_length}"
        )
    
    result: list[str] = []
    index = 0

    for op in cs.ops:
        if isinstance(op, Retain):
            result.append(document[index: index + op.count])
            index += op.count

        elif isinstance(op, Insert):
            result.append(op.text)
        
        elif isinstance(op, Delete):
            index += op.count
        
        else:
            raise TypeError(f"Unknown operation: {op}")
        
    if index != len(document):
        raise ValueError("Changeset did not consume the full document")
    
    return "".join(result)

# doc = "baseball"

# a = changeset(
#     base_length=len(doc),
#     ops=[
#         retain(2),
#         insert("si"),
#         delete(5),
#         retain(1),
#     ],
# )

# print(apply_changeset(doc, a))
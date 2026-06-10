from ot_engine.iterators.op_iterator import OpIterator
from ot_engine.models.operation import *
from ot_engine.models.change_set import ChangeSet
from ot_engine.utils.constructors import *
from ot_engine.utils.apply_changeset import apply_changeset

def transform(A: ChangeSet, B: ChangeSet, isAFirst: bool) -> ChangeSet:
    A_iter = OpIterator(A.ops)
    B_iter = OpIterator(B.ops)

    result = []

    while A_iter.has_next() or B_iter.has_next():
        op_a = A_iter.peek()
        op_b = B_iter.peek()

        if op_b is None:
            if isinstance(op_a, Insert):
                result.append(Retain(len(op_a.text)))
            A_iter.consume()
            continue

        if op_a is None:
            result.append(op_b)
            B_iter.consume()
            continue

        if isinstance(op_a, Insert) and isinstance(op_b, Insert):
            if isAFirst:
                result.append(Retain(len(op_a.text)))
                result.append(Insert(op_b.text))
            else:
                result.append(Insert(op_b.text))
                result.append(Retain(len(op_a.text)))
            
            A_iter.consume()
            B_iter.consume()
            continue

        if isinstance(op_a, Insert):
            result.append(Retain(len(op_a.text)))
            A_iter.consume()
            continue
        if isinstance(op_b, Insert):
            result.append(Insert(op_b.text))
            B_iter.consume()
            continue

        n = min(op_a.length, op_b.length)

        if isinstance(op_a, Retain) and isinstance(op_b, Retain):
            result.append(Retain(n))
        
        elif isinstance(op_a, Retain) and isinstance(op_b, Delete):
            result.append(Delete(n))
        
        elif isinstance(op_a, Delete) and isinstance(op_b, Retain):
            pass

        elif isinstance(op_a, Delete) and isinstance(op_b, Delete):
            pass

        else:
            raise TypeError(f"Unhandled transform case: {op_a}, {op_b}")
        
        A_iter.consume(n)
        B_iter.consume(n)
    
    return changeset(base_length=A.target_length, ops=result)
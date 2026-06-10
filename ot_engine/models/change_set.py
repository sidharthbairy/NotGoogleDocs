from dataclasses import dataclass
from ot_engine.models.operation import Retain, Insert, Delete, Op

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
        

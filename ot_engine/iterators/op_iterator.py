from ot_engine.models.operation import *

class OpIterator:
    def __init__(self, ops: tuple[Op, ...]):
        self.ops = ops
        self.index = 0
        self.offset = 0

    def has_next(self) -> bool:
        return self.index < len(self.ops)
    
    def peek(self) -> Op | None:
        if not self.has_next():
            return None
        
        op = self.ops[self.index]

        if isinstance(op, Retain):
            return Retain(op.count - self.offset)
        
        if isinstance(op, Delete):
            return Delete(op.count - self.offset)
        
        if isinstance(op, Insert):
            return Insert(op.text[self.offset:])
        
        raise TypeError(f"Unknown operation: {op}")
    
    def consume(self, amount: int | None = None) -> None:
        if not self.has_next():
            raise ValueError("Cannot consume past end")
        
        op = self.ops[self.index]

        if isinstance(op, Insert):
            remaining = len(op.text) - self.offset
        else: 
            remaining = op.count - self.offset

        if amount is None:
            amount = remaining

        if amount <= 0:
            raise ValueError("Consume amount must be positive")

        if amount > remaining:
            raise ValueError("Cannot consume more than remaining op length")

        self.offset += amount

        if self.offset == (len(op.text) if isinstance(op, Insert) else op.count):
            self.index += 1
            self.offset = 0
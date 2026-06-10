from __future__ import annotations

from dataclasses import dataclass
from typing import Union

@dataclass(frozen=True)
class Retain:
    count: int

    def __post_init__(self):
        if self.count < 0:
            raise ValueError("Retain count must be positive")
        
    @property
    def length(self) -> int:
        return self.count

@dataclass(frozen=True)
class Insert:
    text: str

    def __post_init__(self):
        if self.text == "":
            raise ValueError("Insert text cannot be empty")
        
    @property
    def length(self) -> int:
        return len(self.text)
    
@dataclass(frozen=True)
class Delete:
    count: int

    def __post_init__(self):
        if self.count < 0:
            raise ValueError("Delete count must be positive")
        
    @property
    def length(self) -> int:
        return self.count
    
Op = Union[Retain, Insert, Delete]

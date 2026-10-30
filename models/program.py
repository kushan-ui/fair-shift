"""Training Program domain model"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class Program:
    id: str
    name: str
    description: str = ""
    capacity: int = 0
    required_attributes: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capacity": self.capacity,
            "required_attributes": self.required_attributes,
            "is_active": int(self.is_active),
            "created_at": self.created_at
        }

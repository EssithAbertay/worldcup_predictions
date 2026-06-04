from dataclasses import dataclass
from typing import List

@dataclass
class TopUser:
    user: User
    predictions: List
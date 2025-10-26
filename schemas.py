from pydantic import BaseModel
from datetime import datetime
from typing import Optional
class PlayerCreate(BaseModel):
    nickname:str
class PlayerOut(BaseModel):
    id:int
    nickname:str
    wins:int
    losses:int
    draws:int
    created_at:datetime
    class Config:
        orm_mode=True
class MatchOut(BaseModel):
    id:int
    player1_id:int
    player2_id:int
    status:str
    winner:Optional[str]
    created_at:datetime
    class config:
        orm_mode=True
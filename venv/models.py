from sqlalchemy import Column,Integer,String,DateTime,ForeignKey,Enum,create_engine
from sqlalchemy.orm import relationship,sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum
Base=declarative_base()
class MatchStatus(enum.Enum):
    waiting="waiting"
    playing="playing"
    finished="finished"
class Player(Base):
    __tablename__="players"
    id=Column(Integer,primary_key=True,autoincrement=True)
    nickname=   Column(String(50),unique=True,nullable=False)
    wins=Column(Integer,default=0)
    losses=Column(Integer,default=0)
    draws=Column(Integer,default=0)
    created_at=Column(DateTime,default=datetime.utcnow)
class Match(Base):
    __tablename__="matches"
    id=Column(Integer,primary_key=True,autoincrement=True)
    player1_id=Column(Integer,ForeignKey("players.id"))
    player2_id=Column(Integer,ForeignKey("players.id"))
    status=Column(Enum(MatchStatus),default=MatchStatus.waiting)
    winner=Column(String(50),nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    player1=relationship("Player",foreign_keys=[player1_id])
    player2=relationship("Player",foreign_keys=[player2_id])
def get_session():
    engine = create_engine("sqlite:///tic_tac_toe.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

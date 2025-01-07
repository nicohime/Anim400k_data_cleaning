
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Boolean

# 新数据库路径
DATABASE_URL = "sqlite:///./models/test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类
Base = declarative_base()

# 数据表模型
class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    counter = Column(Integer, default=0)
    max_counter = Column(Integer, default=10)

class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer)
    user_id = Column(String)
    front_face = Column(Boolean)  # True: 可用, False: 不可用
    voice_match = Column(Boolean)
    background_check = Column(Boolean)
    visual_interference = Column(Boolean)
    duration_check = Column(Boolean)

# 创建表
#Base.metadata.create_all(bind=engine)

print("Tables created successfully in test.db")

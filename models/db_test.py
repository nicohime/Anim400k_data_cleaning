from models.database import SessionLocal, Video

db = SessionLocal()

try:
    # 打印所有表名
    from sqlalchemy import inspect
    inspector = inspect(db.get_bind())
    tables = inspector.get_table_names()
    print("Tables in database:", tables)

    # 打印 Video 表中的所有数据
    videos = db.query(Video).all()
    print(f"Found {len(videos)} videos:")
    for video in videos:
        print(f"ID: {video.id}, URL: {video.url}, Counter: {video.counter}, Max Counter: {video.max_counter}")
finally:
    db.close()

from sqlalchemy import text


result = db.execute(text("SELECT * FROM videos")).fetchall()
for row in result:
    print(row)
from models.database import SessionLocal

print(f"Connecting to: {SessionLocal.kw['bind'].engine.url}")

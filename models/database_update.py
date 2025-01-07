import os

# 视频文件所在的本地路径
VIDEO_DIR = "E:/anime40k/one_face_every_20_4000_sp"

def get_video_files(video_dir):
    """扫描目录中的所有视频文件"""
    video_files = []
    for root, dirs, files in os.walk(video_dir):
        for file in files:
            if file.endswith((".mp4", ".avi", ".mkv")):  # 支持的视频格式
                # 记录相对路径（相对于根目录）
                relative_path = os.path.relpath(os.path.join(root, file), video_dir)
                video_files.append(relative_path)
    return video_files

# 扫描目录
videos = get_video_files(VIDEO_DIR)
print(f"发现 {len(videos)} 个视频文件")


from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.database import Video, Base

DATABASE_URL = "sqlite:///./test.db"  # 替换为您的数据库 URL
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 初始化数据库
Base.metadata.create_all(bind=engine)

# 视频文件托管的公共 URL 前缀
VIDEO_BASE_URL = "https://anim400k.nicohime.com/"

def populate_videos_to_db(video_files):
    """将视频信息插入数据库"""
    db = SessionLocal()
    for video_file in video_files:
        video_url = f"{VIDEO_BASE_URL}{video_file}"  # 构建完整 URL
        db.add(Video(url=video_url, counter=0, max_counter=10))
    db.commit()
    db.close()

# 插入视频数据
video_files = get_video_files(VIDEO_DIR)
populate_videos_to_db(video_files)

print("视频信息已成功导入数据库！")

print("视频信息已成功导入数据库！")

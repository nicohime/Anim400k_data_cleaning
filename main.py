import hashlib
import hmac
import secrets

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
from random import sample, shuffle
from random import choice
from sqlalchemy import func

from models.database import SessionLocal, Video, Annotation  # 导入数据库设置和模型
import uuid
from fastapi import FastAPI, Request, Response, Cookie
import uuid

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware



# FastAPI app
app = FastAPI()

SECRET_KEY_ANNOTATION = "ayaneru"
SECRET_KEY_SUCCESS = "inorin"


# 加密与验证逻辑
def generate_session_id():
    return secrets.token_hex(16)

def encrypt_session_id(session_id, secret_key):
    return hmac.new(secret_key.encode(), session_id.encode(), hashlib.sha256).hexdigest()

def verify_session_id(session_id, hashed_id, secret_key):
    expected_hashed_id = encrypt_session_id(session_id, secret_key)
    return hmac.compare_digest(expected_hashed_id, hashed_id)




# 配置静态文件和模板目录
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 数据模型
class AnnotationData(BaseModel):
    video_id: int
    user_id: str
    front_face: bool
    voice_match: bool
    background_check: bool
    visual_interference: bool
    duration_check: bool



# 后端用于生成 hashed_session_id 的接口
@app.get("/generate_hashed_session")
def generate_hashed_session(request: Request, session_id: str):
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    # 生成 hashed_session_id
    hashed_session_id = encrypt_session_id(session_id, SECRET_KEY_ANNOTATION)

    # 返回给前端
    return {"hashed_session_id": hashed_session_id}

# 后端标注页面接口，验证 session_id 和 hashed_session_id
@app.get("/annotation", response_class=HTMLResponse)
def annotation_page(request: Request, session_hashed: str = Query(None), session_id: str = Cookie(None)):
    print("Received session_id (from cookie):", session_id)
    print("Received session_hashed (from URL):", session_hashed)

    if not session_id or not session_hashed:
        raise HTTPException(status_code=400, detail="Missing session_id or session_hashed")

    print(verify_session_id(session_id, session_hashed, SECRET_KEY_SUCCESS))
    # 验证 session_id 和 session_hashed
    if not verify_session_id(session_id, session_hashed, SECRET_KEY_ANNOTATION):
        raise HTTPException(status_code=400, detail="Invalid session")

    # 返回标注页面
    return templates.TemplateResponse("annotation.html", {"request": request})


# 路由
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """返回主页"""
    return templates.TemplateResponse("index.html", {"request": request})



@app.get("/videos/random")
def get_random_videos():
    """从数据库中随机获取视频并返回完整的 URL 列表，确保有一个校验视频"""
    db = SessionLocal()

    # 获取校验视频
    check_video = db.query(Video).filter(Video.check_video == True, Video.counter < Video.max_counter).first()
    if not check_video:
        raise HTTPException(status_code=400, detail="No check video available.")

    # 获取非校验视频，按 counter 分组并随机选择
    non_check_videos = []
    for counter_value in range(0, 101):  # 假设最大 counter 不超过 100
        videos = db.query(Video).filter(Video.check_video == False, Video.counter == counter_value, Video.counter < Video.max_counter).all()
        if videos:
            non_check_videos.extend(videos)
        if len(non_check_videos) >= 11:
            break

    if len(non_check_videos) < 11:
        raise HTTPException(status_code=400, detail="Not enough non-check videos available.")

    # 从非校验视频中随机选择11个
    selected_videos = sample(non_check_videos, 11)
    selected_videos.append(check_video)  # 确保选中的视频中有一个校验视频
    shuffle(selected_videos)  # 打乱顺序

    db.close()

    return [
        {"id": video.id, "url": f"{video.url}"}
        for video in selected_videos
    ]
@app.get("/annotation-success", response_class=HTMLResponse)
def annotation_success(request: Request, session_id: str = Cookie(None), session_hashed: str = None, response: Response = None):
    if not session_id or not session_hashed:
        return templates.TemplateResponse("error.html", {"request": request})
    if not verify_session_id(session_id, session_hashed, SECRET_KEY_SUCCESS):
        return templates.TemplateResponse("error.html", {"request": request})

    # 删除 session_id 的 cookie，防止多次提交
    response.delete_cookie("session_id", path="/")  # 确保路径与设置 cookie 时相同

    return templates.TemplateResponse("annotation_success.html", {"request": request}, headers=response.headers)


from fastapi.responses import JSONResponse

@app.post("/annotations/upload")
def upload_annotations(annotations: List[AnnotationData], response: Response, session_id: str = Cookie(None)):
    if not session_id:
        raise HTTPException(status_code=403, detail="Session expired")

    db = SessionLocal()
    try:
        is_check_video_valid = False

        # 遍历用户上传的标注数据
        for annotation in annotations:
            video = db.query(Video).filter(Video.id == annotation.video_id).first()
            if not video:
                continue  # 跳过不存在的视频

            if video.check_video:
                # 如果是校验视频，检查标注是否与标准标注完全一致
                standard_annotation = db.query(Annotation).filter(Annotation.video_id == video.id, Annotation.user_id == -2).first()
                if not standard_annotation or (
                    standard_annotation.front_face != annotation.front_face or
                    standard_annotation.voice_match != annotation.voice_match or
                    standard_annotation.background_check != annotation.background_check or
                    standard_annotation.visual_interference != annotation.visual_interference or
                    standard_annotation.duration_check != annotation.duration_check
                ):
                    db.rollback()
                    return JSONResponse(
                        status_code=422,
                        content={"message": "校验视频标注不正确，请检查您的标注后重试。"}
                    )
                is_check_video_valid = True
                continue  # 校验视频不需要写入标注数据

        if not is_check_video_valid:
            db.rollback()
            raise HTTPException(status_code=400, detail="No valid check video annotation found.")

        # 处理非校验视频的标注数据
        for annotation in annotations:
            video = db.query(Video).filter(Video.id == annotation.video_id).first()
            if not video or video.check_video:
                continue  # 跳过不存在的视频和校验视频

            # 写入标注数据
            db.add(Annotation(
                video_id=annotation.video_id,
                user_id=annotation.user_id,
                front_face=annotation.front_face,
                voice_match=annotation.voice_match,
                background_check=annotation.background_check,
                visual_interference=annotation.visual_interference,
                duration_check=annotation.duration_check
            ))
            video.counter += 1  # 更新计数

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error during data submission: {str(e)}")
    finally:
        db.close()

    # 生成 hashed_id，直接使用当前 session_id 来加密
    hashed_id = encrypt_session_id(session_id, SECRET_KEY_SUCCESS)

    # 设置 session_id cookie（如果需要更新 cookie）
    response.set_cookie("session_id", session_id, httponly=True, secure=True)

    # 返回上传成功和重定向 URL
    return {"message": "Annotations uploaded successfully",
            "redirect_url": f"/annotation-success?session_hashed={hashed_id}"}



@app.post("/user/create")
def create_user():
    user_id = str(uuid.uuid4())
    response = JSONResponse({"user_id": user_id})
    response.set_cookie(
        key="user_id",
        value=user_id,
        max_age=365*24*60*60,
        path="/",
        httponly=False  # 移除 HttpOnly
    )
    return response




# 硬链接及其正确答案
TUTORIAL_VIDEOS = [
    {"id": 1, "url": "https://anim400k.nicohime.com/00d6d2eb-fead-46cc-b572-425c826a982d.mp4", "correct_answers": {
        "front_face": True,
        "voice_match": True,
        "background_check": True,
        "visual_interference": False,
        "duration_check": True,
    }},
    {"id": 2, "url": "https://anim400k.nicohime.com/0c0ac371-d914-4510-b244-d202037fd013.mp4", "correct_answers": {
        "front_face": True,
        "voice_match": True,
        "background_check": True,
        "visual_interference": False,
        "duration_check": True,
    }},
    {"id": 3, "url": "https://anim400k.nicohime.com/18df0cc2-35bf-495c-8649-65e6d17ba1c9.mp4", "correct_answers": {
        "front_face": True,
        "voice_match": True,
        "background_check": True,
        "visual_interference": False,
        "duration_check": True,
    }},
    {"id": 4, "url": "https://anim400k.nicohime.com/246a6290-7c48-4802-953d-20661d442182.mp4", "correct_answers": {
        "front_face": True,
        "voice_match": True,
        "background_check": True,
        "visual_interference": False,
        "duration_check": True,
    }},
    {"id": 5, "url": "https://anim400k.nicohime.com/30d5a6d2-5c77-44c1-9dcb-552e0b0abf42.mp4", "correct_answers": {
        "front_face": True,
        "voice_match": True,
        "background_check": True,
        "visual_interference": False,
        "duration_check": True,
    }},
    {"id": 6, "url": "https://anim400k.nicohime.com/70adcdc7-e315-40ec-8ba1-bc974946fc4c.mp4", "correct_answers": {
        "front_face": True,
        "voice_match": True,
        "background_check": True,
        "visual_interference": False,
        "duration_check": True,
    }},
    {"id": 7, "url": "https://anim400k.nicohime.com/927ddda6-34af-4982-bedf-136a687566ff.mp4", "correct_answers": {
        "front_face": True,
        "voice_match": True,
        "background_check": True,
        "visual_interference": False,
        "duration_check": True,
    }},
]

@app.get("/tutorial")
def tutorial_page(request: Request):
    """返回教程页面"""
    return templates.TemplateResponse("tutorial.html", {"request": request})


@app.get("/videos/tutorial_random")
def get_tutorial_video():
    """随机抽取一个教程视频"""
    #print("进入了教程视频选择路由!")  #
    video = choice(TUTORIAL_VIDEOS)
    #print(video)
    return {"id": video["id"], "url": video["url"]}


class TutorialValidationData(BaseModel):
    video_id: int
    user_id: int  # 用户 ID 在教程阶段为 -1
    front_face: bool
    voice_match: bool
    background_check: bool
    visual_interference: bool
    duration_check: bool


@app.post("/tutorial/validate")
async def validate_tutorial(validation_data: TutorialValidationData):
    """校验用户提交的教程标注是否正确"""

    # 检查 user_id 是否是教程阶段的临时值（-1），若不是，返回错误
    if validation_data.user_id != -1:
        raise HTTPException(status_code=400, detail="Invalid user ID for tutorial")

    # 根据视频 ID 获取正确答案
    video = next((v for v in TUTORIAL_VIDEOS if v["id"] == validation_data.video_id), None)
    if not video:
        raise HTTPException(status_code=400, detail="Invalid video ID")

    correct_answers = video["correct_answers"]

    # 比较用户提交的答案与正确答案
    for field, expected in correct_answers.items():
        user_answer = getattr(validation_data, field)
        if user_answer != expected:
            raise HTTPException(status_code=400, detail=f"Incorrect answer.")

    # 生成 session_id 并加密
    session_id = generate_session_id()

    # 将 session_id 写入 Cookie
    response = JSONResponse({"message": "Validation successful", "session_id": session_id})
    response.set_cookie(key="session_id", value=session_id, httponly=True, path="/")
    print("Generated session_id:", session_id)

    return response


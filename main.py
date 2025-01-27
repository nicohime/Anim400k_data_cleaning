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
    """从数据库中随机获取视频并返回完整的 URL 列表，确保有两个校验视频和十个未标注视频"""
    db = SessionLocal()

    # 获取所有校验视频
    check_videos = db.query(Video).filter(Video.check_video == True, Video.counter < Video.max_counter).all()

    if not check_videos:
        raise HTTPException(status_code=400, detail="Not enough check videos available.")

    # 筛选校验标签值完全为 True 和部分为 False 的视频
    check_videos_true = []
    check_videos_partial = []

    for video in check_videos:
        annotation = db.query(Annotation).filter(Annotation.video_id == video.id).first()
        if not annotation:
            continue

        if (annotation.front_face and annotation.voice_match and annotation.background_check and
            annotation.visual_interference and annotation.duration_check):
            check_videos_true.append(video)
        else:
            check_videos_partial.append(video)

    if len(check_videos_true) < 1 or len(check_videos_partial) < 1:
        raise HTTPException(status_code=400, detail="Not enough valid check videos available.")

    # 随机选择一个完全校验通过的视频和一个部分校验通过的视频
    selected_check_videos = [
        sample(check_videos_true, 1)[0],
        sample(check_videos_partial, 1)[0]
    ]

    # 获取未标注视频，按 counter 分组并随机选择
    non_check_videos = []
    for counter_value in range(0, 101):  # 假设最大 counter 不超过 100
        videos = db.query(Video).filter(Video.check_video == False, Video.counter == counter_value, Video.counter < Video.max_counter).all()
        if videos:
            non_check_videos.extend(videos)
        if len(non_check_videos) >= 10:
            break

    if len(non_check_videos) < 10:
        raise HTTPException(status_code=400, detail="Not enough non-check videos available.")

    # 从未标注视频中随机选择10个
    selected_non_check_videos = sample(non_check_videos, 10)

    # 合并视频列表并打乱顺序
    selected_videos = selected_check_videos + selected_non_check_videos
    shuffle(selected_videos)

    db.close()

    return [
        {"id": video.id, "url": f"{video.url}"}
        for video in selected_videos
    ]


@app.get("/annotation-success", response_class=HTMLResponse)
def annotation_success(
    request: Request,
    session_id: str = Cookie(None),
    session_hashed: str = None,
    user_id: str = Cookie(None),  # 从 Cookie 中提取 user_id
    response: Response = None
):
    if not session_id or not session_hashed or not user_id:
        return templates.TemplateResponse("error.html", {"request": request})
    if not verify_session_id(session_id, session_hashed, SECRET_KEY_SUCCESS):
        return templates.TemplateResponse("error.html", {"request": request})

    # 删除 session_id 的 cookie，防止多次提交
    response.delete_cookie("session_id", path="/")  # 确保路径与设置 cookie 时相同

    # 将 user_id 传递给模板
    return templates.TemplateResponse(
        "annotation_success.html",
        {"request": request, "user_id": user_id},
        headers=response.headers
    )



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
                # 获取标准标注数据
                standard_annotation = db.query(Annotation).filter(
                    Annotation.video_id == video.id, Annotation.user_id == -2
                ).first()

                if not standard_annotation:
                    db.rollback()
                    return JSONResponse(
                        status_code=422,
                        content={"message": "校验视频缺少标准标注，请检查后重试。"}
                    )

                # 校验逻辑：检查标准标注的五个字段
                standard_values = [
                    standard_annotation.front_face,
                    standard_annotation.voice_match,
                    standard_annotation.background_check,
                    standard_annotation.visual_interference,
                    standard_annotation.duration_check
                ]
                user_values = [
                    annotation.front_face,
                    annotation.voice_match,
                    annotation.background_check,
                    annotation.visual_interference,
                    annotation.duration_check
                ]

                if all(value == 1 for value in standard_values):
                    # 如果标准标注五个字段都为1，用户标注必须完全一致
                    if standard_values != user_values:
                        db.rollback()
                        return JSONResponse(
                            status_code=422,
                            content={"message": "映像判断の結果が正しくありません、確認して再試行してください。"}
                        )
                else:
                    # 如果标准标注存在不为1的字段，用户标注的五个标签中至少有一个为 false
                    if all(user == 1 for user in user_values):
                        db.rollback()
                        return JSONResponse(
                            status_code=422,
                            content={"message": "映像判断の結果が正しくありません、確認して再試行してください。"}
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
        "visual_interference": True,
        "duration_check": False,
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
    print(validation_data)
    # 比较用户提交的答案与正确答案，忽略 duration_check 字段
    for field, expected in correct_answers.items():
        if field == "duration_check":  # 跳过 duration_check 字段
            continue
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


document.addEventListener("DOMContentLoaded", async () => {
    const videoContainer = document.getElementById("video-container");
    const submitBtn = document.getElementById("submit-btn");

    let tutorialVideoId;

    // 加载教程视频
    const loadTutorialVideo = async () => {
        try {
            const response = await fetch("/videos/tutorial_random");
            if (!response.ok) throw new Error("Failed to load tutorial video");
            const videoData = await response.json();
            tutorialVideoId = videoData.id;

            // 插入视频和标注维度
            videoContainer.innerHTML = `
                <video width="320" height="240" controls>
                    <source src="${videoData.url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                <div>
                    <label class="radio-label">
                        <input type="radio" name="front_face" value="true"> 前脸可用
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="front_face" value="false"> 前脸不可用
                    </label>
                </div>
                <div>
                    <label class="radio-label">
                        <input type="radio" name="voice_match" value="true"> 语音匹配可用
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="voice_match" value="false"> 语音匹配不可用
                    </label>
                </div>
                <div>
                    <label class="radio-label">
                        <input type="radio" name="background_check" value="true"> 背景检查可用
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="background_check" value="false"> 背景检查不可用
                    </label>
                </div>
                <div>
                    <label class="radio-label">
                        <input type="radio" name="visual_interference" value="true"> 视觉干扰可用
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="visual_interference" value="false"> 视觉干扰不可用
                    </label>
                </div>
                <div>
                    <label class="radio-label">
                        <input type="radio" name="duration_check" value="true"> 持续时间检查可用
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="duration_check" value="false"> 持续时间检查不可用
                    </label>
                </div>
            `;
        } catch (error) {
            console.error("Error loading tutorial video:", error);
        }
    };

    // 提交教程标注
    const submitTutorialAnnotation = async () => {
        const annotation = {
            video_id: tutorialVideoId,
            user_id: -1, // 默认用户 ID 为 -1
            front_face: document.querySelector("input[name='front_face']:checked")?.value === "true",
            voice_match: document.querySelector("input[name='voice_match']:checked")?.value === "true",
            background_check: document.querySelector("input[name='background_check']:checked")?.value === "true",
            visual_interference: document.querySelector("input[name='visual_interference']:checked")?.value === "true",
            duration_check: document.querySelector("input[name='duration_check']:checked")?.value === "true",
        };

        if (Object.values(annotation).some(value => value === undefined)) {
            alert("请完成所有标注！");
            return;
        }

        try {
            const response = await fetch("/tutorial/validate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(annotation),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Validation failed");
            }

            const responseData = await response.json();
            const sessionId = responseData.session_id;  // 从后端返回的 session_id

            // 将 session_id 存储到 cookie 中
            document.cookie = `session_id=${sessionId}; path=/; Secure; HttpOnly; SameSite=Strict`;

            alert("标注成功，进入正式打标页面！");

            // 请求后端生成 hashed_session_id 并跳转
            const redirectResponse = await fetch(`/generate_hashed_session?session_id=${sessionId}`);
            const redirectData = await redirectResponse.json();

            if (redirectData && redirectData.hashed_session_id) {
                window.location.href = `/annotation?session_hashed=${redirectData.hashed_session_id}`;
            }
        } catch (error) {
            alert(`标注错误: ${error.message}`);
            window.location.reload();
        }
    };


    // 初始化教程页面
    submitBtn.addEventListener("click", submitTutorialAnnotation);
    await loadTutorialVideo();
});

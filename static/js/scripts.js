document.addEventListener("DOMContentLoaded", () => {
     const videoContainer = document.getElementById("video-container");
    const submitBtn = document.getElementById("submit-btn");

    // 获取 cookie 的函数
    const getCookie = (name) => {
        const cookies = document.cookie.split("; ");
        for (const cookie of cookies) {
            const [key, value] = cookie.split("=");
            if (key === name) return decodeURIComponent(value);
        }
        return null;
    };

    // 设置 cookie 的函数
    const setCookie = (name, value, days) => {
        const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`;
    };

    // 获取或创建 user_id 的函数
    const getOrCreateUserId = async () => {
        // 尝试从 cookie 获取 user_id
        let userId = getCookie("user_id");
        console.log("check user id history",userId);

        // 如果 cookie 中没有 user_id，则从服务器请求一个新的
        if (!userId) {
            try {
                // 向后端请求生成 user_id
                const response = await fetch("/user/create", { method: "POST" });
                if (!response.ok) {
                    throw new Error("Failed to fetch user ID from backend");
                }
                const data = await response.json();
                userId = data.user_id;
                console.log("No userid, get a new one",userId);
                console.log("Before generation:", document.cookie)
                // 存储到 cookie
                setCookie("user_id", userId, 365);
                console.log("Check generation:", document.cookie);// 设置 cookie 有效期 1 年
            } catch (error) {
                console.error("Error fetching user ID:", error);
                return null; // 如果获取失败，则返回 null
            }
        }

        return userId;  // 返回获取到的 user_id（无论是从 cookie 还是服务器）
    };



    // 获取或创建 user_id
    const init = async () => {
        const userId = await getOrCreateUserId();
        if (!userId) {
            alert("无法获取或创建 user_id，请稍后再试！");
            return;
        }

        console.log("Existing cookie:", document.cookie);
        console.log("Fetched user_id from backend:", userId);
        console.log("Stored cookie user_id:", getCookie("user_id"));

        const results = []; // 收集标注结果
        let videoIds = []; // 记录视频的 ID，用于校验是否所有视频都已标注

        // 请求后端获取视频列表
        try {
            const response = await fetch("/videos/random");
            const videoData = await response.json();
            videoIds = videoData.map(video => video.id); // 保存视频 ID

            // 动态插入视频到页面
            videoData.forEach(video => {
                const videoItem = document.createElement("div");
                videoItem.classList.add("video-item");
                videoItem.innerHTML = `
                    <video width="320" height="240" controls>
                        <source src="${video.url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div>
                        <label class="radio-label">
                            <input type="radio" name="front_face-${video.id}" class="radio-btn" data-id="${video.id}" value="true">
                            <span class="circle"></span> 前脸可用
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="front_face-${video.id}" class="radio-btn" data-id="${video.id}" value="false">
                            <span class="circle"></span> 前脸不可用
                        </label>
                    </div>
                    <div>
                        <label class="radio-label">
                            <input type="radio" name="voice_match-${video.id}" class="radio-btn" data-id="${video.id}" value="true">
                            <span class="circle"></span> 语音匹配可用
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="voice_match-${video.id}" class="radio-btn" data-id="${video.id}" value="false">
                            <span class="circle"></span> 语音匹配不可用
                        </label>
                    </div>
                    <div>
                        <label class="radio-label">
                            <input type="radio" name="background_check-${video.id}" class="radio-btn" data-id="${video.id}" value="true">
                            <span class="circle"></span> 背景检查可用
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="background_check-${video.id}" class="radio-btn" data-id="${video.id}" value="false">
                            <span class="circle"></span> 背景检查不可用
                        </label>
                    </div>
                    <div>
                        <label class="radio-label">
                            <input type="radio" name="visual_interference-${video.id}" class="radio-btn" data-id="${video.id}" value="true">
                            <span class="circle"></span> 视觉干扰可用
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="visual_interference-${video.id}" class="radio-btn" data-id="${video.id}" value="false">
                            <span class="circle"></span> 视觉干扰不可用
                        </label>
                    </div>
                    <div>
                        <label class="radio-label">
                            <input type="radio" name="duration_check-${video.id}" class="radio-btn" data-id="${video.id}" value="true">
                            <span class="circle"></span> 持续时间检查可用
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="duration_check-${video.id}" class="radio-btn" data-id="${video.id}" value="false">
                            <span class="circle"></span> 持续时间检查不可用
                        </label>
                    </div>
                `;
                videoContainer.appendChild(videoItem);

                // 为每个视频的单选按钮绑定事件监听器
                const radioButtons = videoItem.querySelectorAll(".radio-btn");
                radioButtons.forEach(radio => {
                    radio.addEventListener("change", () => {
                        const videoId = parseInt(radio.getAttribute("data-id"));
                        const fieldName = radio.name.split("-")[0]; // 提取维度名称
                        const label = radio.value === "true";

                        // 检查是否已有标注记录
                        const existingResultIndex = results.findIndex(result => result.video_id === videoId);
                        if (existingResultIndex > -1) {
                            results[existingResultIndex][fieldName] = label; // 更新对应维度的标注
                        } else {
                            // 新的标注记录
                            const result = {
                                video_id: videoId,
                                user_id: userId,
                                front_face: null,
                                voice_match: null,
                                background_check: null,
                                visual_interference: null,
                                duration_check: null
                            };
                            result[fieldName] = label;
                            results.push(result);
                        }

                        console.log("Current Results:", results); // 打印当前结果
                    });
                });
            });
        } catch (error) {
            console.error("加载视频失败:", error);
        }

        // 提交按钮逻辑
        submitBtn.addEventListener("click", () => {
            // 检查是否所有视频都已标注
            const unmarkedVideos = videoIds.filter(id => {
                const videoResult = results.find(result => result.video_id === id);
                return (
                    !videoResult ||
                    Object.entries(videoResult)
                        .filter(([key]) => key !== "video_id" && key !== "user_id")
                        .some(([_, value]) => value === null)
                );
            });

            if (unmarkedVideos.length > 0 || results.length === 0) {
                alert(`还有 ${unmarkedVideos.length || videoIds.length} 个视频未标注，请完成后再提交！`);
                return;
            }

            // 提交到后端
            fetch("/annotations/upload", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(results),
            })
                .then(async response => {
                    if (!response.ok) {
                        // 尝试解析错误响应
                        const errorData = await response.json();
                        if (errorData.message) {
                            throw new Error(errorData.message); // 抛出后端返回的错误消息
                        } else {
                            throw new Error("提交失败，请稍后再试！");
                        }
                    }
                    return response.json(); // 成功响应处理
                })
                .then(data => {
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url; // 跳转到成功页面
                    }
                })
                .catch(error => {
                    // 捕获错误并显示弹窗
                    alert(error.message);
                });
        });


    };

    init(); // 初始化流程
});

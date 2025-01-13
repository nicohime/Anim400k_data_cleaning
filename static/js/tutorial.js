document.addEventListener("DOMContentLoaded", async () => {
    const videoContainer = document.getElementById("video-container");
    const submitBtn = document.getElementById("submit-btn");

    let tutorialVideoId;

    // Load tutorial video
    const loadTutorialVideo = async () => {
        try {
            const response = await fetch("/videos/tutorial_random");
            if (!response.ok) throw new Error("Failed to load tutorial video");
            const videoData = await response.json();
            tutorialVideoId = videoData.id;

            // Insert video and annotation options
            videoContainer.innerHTML = `
                <video width="320" height="240" controls>
                    <source src="${videoData.url}" type="video/mp4">
                    あなたのブラウザはビデオタグをサポートしていません。
                </video>
                <div id="options-container">
                    <div class="radio-group">
                        <label class="radio-label">
                            <input type="radio" name="front_face" value="true"> 正面が見える
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="front_face" value="false"> 正面が見えない
                        </label>
                    </div>
                    <div class="radio-group">
                        <label class="radio-label">
                            <input type="radio" name="voice_match" value="true"> 音声と映像が一致
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="voice_match" value="false"> 音声と映像が一致しない
                        </label>
                    </div>
                    <div class="radio-group">
                        <label class="radio-label">
                            <input type="radio" name="background_check" value="true"> シンプルで素朴な背景
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="background_check" value="false"> 複雑で混乱した背景
                        </label>
                    </div>
                    <div class="radio-group">
                        <label class="radio-label">
                            <input type="radio" name="visual_interference" value="true"> 顔に干渉なし
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="visual_interference" value="false"> 顔に干渉あり
                        </label>
                    </div>
                    <div class="radio-group">
                        <label class="radio-label">
                            <input type="radio" name="duration_check" value="true"> 3秒以上の時間で同時にすべての規則を満たす
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="duration_check" value="false"> 3秒以上の時間で同時にすべての規則を満たさない
                        </label>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error("Error loading tutorial video:", error);
        }
    };

    // Submit tutorial annotation
    const submitTutorialAnnotation = async () => {
        const annotation = {
            video_id: tutorialVideoId,
            user_id: -1, // Default user ID is -1
            front_face: document.querySelector("input[name='front_face']:checked")?.value === "true",
            voice_match: document.querySelector("input[name='voice_match']:checked")?.value === "true",
            background_check: document.querySelector("input[name='background_check']:checked")?.value === "true",
            visual_interference: document.querySelector("input[name='visual_interference']:checked")?.value === "true",
            duration_check: document.querySelector("input[name='duration_check']:checked")?.value === "true",
        };

        if (Object.values(annotation).some(value => value === undefined)) {
            alert("すべてのアノテーションを完了してください！");
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
                throw new Error(errorData.detail || "バリデーションに失敗しました");
            }

            const responseData = await response.json();
            const sessionId = responseData.session_id;  // Session ID returned from backend

            // Store session_id in cookie
            document.cookie = `session_id=${sessionId}; path=/; Secure; HttpOnly; SameSite=Strict`;

            alert("アノテーションが成功しました。正式なアノテーションページに移動します！");

            // Request backend to generate hashed_session_id and redirect
            const redirectResponse = await fetch(`/generate_hashed_session?session_id=${sessionId}`);
            const redirectData = await redirectResponse.json();

            if (redirectData && redirectData.hashed_session_id) {
                window.location.href = `/annotation?session_hashed=${redirectData.hashed_session_id}`;
            }
        } catch (error) {
            alert(`アノテーションエラー: ${error.message}`);
            window.location.reload();
        }
    };

    // Initialize tutorial page
    submitBtn.addEventListener("click", submitTutorialAnnotation);
    await loadTutorialVideo();
});

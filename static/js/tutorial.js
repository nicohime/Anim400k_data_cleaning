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

            <div>
                <p>1. 正面の顔（両目、鼻、口がはっきりと見える顔）がはっきりと見え、かつその状態が3秒以上続く場面はありますか？</p>
                <label class="radio-label">
                    <input type="radio" name="front_face-${videoData.id}" class="radio-btn" data-id="${videoData.id}" value="true" onchange="showQuestion(${videoData.id}, 1, true)">
                    はい
                </label>
                <label class="radio-label">
                    <input type="radio" name="front_face-${videoData.id}" class="radio-btn" data-id="${videoData.id}" value="false" onchange="showQuestion(${videoData.id}, 1, false)">
                    いいえ
                </label>
            </div>
            <div id="${videoData.id}-2" hidden="hidden">
                <p>2. （1の場面の中で）登場人物が3秒以上話しているシーンはありますか？（心理活動やナレーションなどの話し声は含まれません）</p>
                <label class="radio-label">
                    <input type="radio" name="voice_match-${videoData.id}" class="radio-btn" data-id="${videoData.id}" value="true" onchange="showQuestion(${videoData.id}, 2, true)">
                    はい
                </label>
                <label class="radio-label">
                    <input type="radio" name="voice_match-${videoData.id}" class="radio-btn" data-id="${videoData.id}" value="false" onchange="showQuestion(${videoData.id}, 2, false)">
                    いいえ
                </label>
            </div>
            <div id="${videoData.id}-3" hidden="hidden">
                <p>3. （2の場面の中で）背景はシンプルですか？（激しい照明の変化や激しい戦闘シーンがない）</p>
                <label class="radio-label">
                    <input type="radio" name="background_check-${videoData.id}" class="radio-btn" data-id="${videoData.id}" value="true" onchange="showQuestion(${videoData.id}, 3, true)">
                    はい
                </label>
                <label class="radio-label">
                    <input type="radio" name="background_check-${videoData.id}" class="radio-btn" data-id="${videoData.id}" value="false" onchange="showQuestion(${videoData.id}, 3, false)">
                    いいえ
                </label>
            </div>
            <div id="${videoData.id}-4" hidden="hidden">
                <p>4. （3の場面の中で）他の人物の顔は見えませんか？</p>
                <label class="radio-label">
                    <input type="radio" name="visual_interference-${videoData.id}" class="radio-btn" data-id="${videoData.id}" value="true" >
                    はい
                </label>
                <label class="radio-label">
                    <input type="radio" name="visual_interference-${videoData.id}" class="radio-btn" data-id="${videoData.id}" value="false" >
                    いいえ
                </label>
                <p class="explanation" style="margin-top: 10px; font-size: 14px; color: #555;">
                    この動画は1秒〜5秒の部分において、正面の顔が見え、音声と人物が一致し、複雑な背景や他の人物の登場がないことを満たしています。そのため、すべての選択肢で「はい」を選択してください。
                </p>
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
            front_face: document.querySelector(`input[name='front_face-${tutorialVideoId}']:checked`)?.value === "true",
            voice_match: document.querySelector(`input[name='voice_match-${tutorialVideoId}']:checked`)?.value === "true",
            background_check: document.querySelector(`input[name='background_check-${tutorialVideoId}']:checked`)?.value === "true",
            visual_interference: document.querySelector(`input[name='visual_interference-${tutorialVideoId}']:checked`)?.value === "true",
            duration_check: document.querySelector(`input[name='duration_check-${tutorialVideoId}']:checked`)?.value === "true",
        };

        if (Object.values(annotation).some(value => value === undefined)) {
            alert("すべての映像判断を完了してください！");
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
function showQuestion(videoId, questionId, value) {
    if (value) {
        // 用户选择「是」
        let nextQuestion = document.getElementById(`${videoId}-${questionId + 1}`);
        if (nextQuestion) {
            // 显示下一个问题
            nextQuestion.removeAttribute("hidden");

            // 重置下一个问题及其后续问题的选项为未选择状态
            resetQuestions(videoId, questionId + 1);
        }
    } else {
        // 用户选择「否」
        let currentId = questionId + 1;
        let nextQuestion = document.getElementById(`${videoId}-${currentId}`);

        while (nextQuestion) {
            // 隐藏后续问题
            nextQuestion.setAttribute("hidden", "hidden");

            // 将所有选项设置为「否」
            let radios = nextQuestion.querySelectorAll('input[type="radio"][value="false"]');
            radios.forEach(radio => {
                radio.checked = true;
            });

            // 准备处理下一个问题
            currentId++;
            nextQuestion = document.getElementById(`${videoId}-${currentId}`);
        }
    }
}

// 重置后续问题的选项为未选择状态
function resetQuestions(videoId, fromQuestionId) {
    let nextQuestion = document.getElementById(`${videoId}-${fromQuestionId}`);
    while (nextQuestion) {
        // 获取所有选项并重置为未选择状态
        let radios = nextQuestion.querySelectorAll('input[type="radio"]');
        radios.forEach(radio => {
            radio.checked = false;
        });

        // 准备处理下一个问题
        fromQuestionId++;
        nextQuestion = document.getElementById(`${videoId}-${fromQuestionId}`);
    }
}

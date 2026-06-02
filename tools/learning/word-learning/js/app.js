/**
 * 主应用逻辑
 */

const APP = {
    // 状态
    state: {
        currentScreen: 'welcome',
        currentLevel: 1,
        exercises: [],
        currentExerciseIndex: 0,
        correctCount: 0,
        wrongCount: 0,
        streak: 0,
        isAnswered: false
    },

    // 单词数据
    words: [],

    // 初始化
    init() {
        // 初始化 TTS
        TTS.init();

        // 检查每日重置
        Storage.checkDailyReset();

        // 加载单词数据
        this.loadWords();

        // 绑定事件
        this.bindEvents();

        // 更新界面
        this.updateUI();
    },

    /**
     * 加载单词数据
     */
    loadWords() {
        // 先尝试从 localStorage 缓存加载
        const cached = Storage.getWordCache();
        if (cached && cached.length > 0) {
            this.words = cached;
        } else {
            // 使用示例数据
            this.words = this.getSampleWords();
            Storage.setWordCache(this.words);
        }
    },

    /**
     * 获取示例单词数据
     */
    getSampleWords() {
        return [
            { id: 1, word: 'abandon', meaning: '放弃，遗弃', level: 1, synonyms: ['leave', 'desert', 'quit'] },
            { id: 2, word: 'establish', meaning: '建立，创立', level: 1, synonyms: ['found', 'set up', 'create'] },
            { id: 3, word: 'calculate', meaning: '计算，估计', level: 2, synonyms: ['compute', 'estimate'] },
            { id: 4, word: 'demonstrate', meaning: '证明，演示', level: 2, synonyms: ['show', 'illustrate'] },
            { id: 5, word: 'emphasize', meaning: '强调，着重', level: 2, synonyms: ['stress', 'highlight'] },
            { id: 6, word: 'benefit', meaning: '有益于，受益', level: 1, synonyms: ['help', 'aid', 'profit'] },
            { id: 7, word: 'approach', meaning: '接近，方法', level: 2, synonyms: ['method', 'way', 'technique'] },
            { id: 8, word: 'indicate', meaning: '表明，指示', level: 2, synonyms: ['show', 'suggest', 'imply'] },
            { id: 9, word: 'confirm', meaning: '确认，证实', level: 3, synonyms: ['verify', 'prove', 'validate'] },
            { id: 10, word: 'estimate', meaning: '估计，评估', level: 3, synonyms: ['assess', 'evaluate'] },
            { id: 11, word: 'generate', meaning: '生成，产生', level: 2, synonyms: ['produce', 'create', 'form'] },
            { id: 12, word: 'implement', meaning: '实施，执行', level: 2, synonyms: ['execute', 'carry out'] },
            { id: 13, word: 'require', meaning: '需要，要求', level: 1, synonyms: ['need', 'demand'] },
            { id: 14, word: 'obtain', meaning: '获得，得到', level: 2, synonyms: ['acquire', 'gain', 'get'] },
            { id: 15, word: 'maintain', meaning: '维持，维修', level: 2, synonyms: ['keep', 'preserve', 'sustain'] },
            { id: 16, word: 'significant', meaning: '重要的，重大的', level: 1, synonyms: ['important', 'major', 'key'] },
            { id: 17, word: 'environment', meaning: '环境，外界', level: 1, synonyms: ['surroundings', 'setting'] },
            { id: 18, word: 'research', meaning: '研究，调查', level: 1, synonyms: ['study', 'investigation'] },
            { id: 19, word: 'develop', meaning: '发展，开发', level: 1, synonyms: ['grow', 'advance', 'improve'] },
            { id: 20, word: 'provide', meaning: '提供，供给', level: 1, synonyms: ['give', 'offer', 'supply'] },
            { id: 21, word: 'function', meaning: '功能，作用', level: 2, synonyms: ['role', 'purpose', 'job'] },
            { id: 22, word: 'contribute', meaning: '贡献，捐献', level: 3, synonyms: ['add', 'donate', 'give'] },
            { id: 23, word: 'process', meaning: '过程，加工', level: 2, synonyms: ['procedure', 'method', 'step'] },
            { id: 24, word: 'policy', meaning: '政策，方针', level: 2, synonyms: ['strategy', 'plan', 'guideline'] },
            { id: 25, word: 'analysis', meaning: '分析，分解', level: 3, synonyms: ['examination', 'study'] },
            { id: 26, word: 'concept', meaning: '概念，观念', level: 2, synonyms: ['idea', 'notion', 'thought'] },
            { id: 27, word: 'theory', meaning: '理论，学说', level: 2, synonyms: ['hypothesis', 'assumption'] },
            { id: 28, word: 'relevant', meaning: '相关的，切题的', level: 3, synonyms: ['related', 'pertinent', 'applicable'] },
            { id: 29, word: 'achieve', meaning: '达到，实现', level: 1, synonyms: ['accomplish', 'attain', 'reach'] },
            { id: 30, word: 'determine', meaning: '决定，确定', level: 2, synonyms: ['decide', 'establish', 'fix'] }
        ];
    },

    /**
     * 获取所有单词
     */
    getAllWords() {
        return this.words;
    },

    /**
     * 获取指定级别的单词
     */
    getWordsByLevel(level) {
        return this.words.filter(w => w.level === level);
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 级别选择
        document.querySelectorAll('.level-card').forEach(card => {
            card.addEventListener('click', () => {
                const level = parseInt(card.dataset.level);
                this.startPractice(level);
            });
        });

        // 返回按钮
        document.getElementById('back-btn').addEventListener('click', () => {
            this.showScreen('welcome');
        });

        // 继续学习按钮
        document.getElementById('continue-btn').addEventListener('click', () => {
            this.startPractice(this.state.currentLevel);
        });

        // 复习错题按钮
        document.getElementById('review-btn').addEventListener('click', () => {
            this.startReview();
        });

        // 底部导航
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const screen = item.dataset.screen;
                this.showScreen(screen);
            });
        });

        // 设置按钮
        document.getElementById('settings-btn').addEventListener('click', () => {
            document.getElementById('settings-modal').classList.add('active');
        });

        // 关闭设置
        document.getElementById('close-settings-btn').addEventListener('click', () => {
            document.getElementById('settings-modal').classList.remove('active');
        });

        // TTS 速度
        document.getElementById('tts-speed').addEventListener('input', (e) => {
            const speed = parseFloat(e.target.value);
            Storage.updateSettings({ ttsSpeed: speed });
        });

        // 音效开关
        document.getElementById('sound-toggle').addEventListener('click', (e) => {
            const btn = e.target;
            const settings = Storage.getSettings();
            const newState = !settings.soundEnabled;
            Storage.updateSettings({ soundEnabled: newState });
            btn.textContent = newState ? '开启' : '关闭';
            btn.classList.toggle('off', !newState);
        });

        // 重置进度
        document.getElementById('reset-progress-btn').addEventListener('click', () => {
            if (confirm('确定要重置所有学习进度吗？此操作不可撤销。')) {
                Storage.resetAll();
                location.reload();
            }
        });

        // 关闭统计
        document.getElementById('close-stats-btn').addEventListener('click', () => {
            this.showScreen('welcome');
        });
    },

    /**
     * 显示屏幕
     */
    showScreen(screenName) {
        // 更新导航状态
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.screen === screenName);
        });

        // 更新屏幕显示
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.toggle('active', screen.id === `${screenName}-screen`);
        });

        this.state.currentScreen = screenName;

        // 如果显示统计屏幕，更新数据
        if (screenName === 'stats') {
            this.updateStatsScreen();
        }
    },

    /**
     * 开始练习
     */
    startPractice(level) {
        this.state.currentLevel = level;
        this.state.correctCount = 0;
        this.state.wrongCount = 0;
        this.state.currentExerciseIndex = 0;

        // 根据级别获取练习逻辑
        let levelModule;
        switch (level) {
            case 1: levelModule = BeginnerLevel; break;
            case 2: levelModule = IntermediateLevel; break;
            case 3: levelModule = AdvancedLevel; break;
            default: levelModule = BeginnerLevel;
        }

        // 获取该级别的单词
        const levelWords = this.getWordsByLevel(level);
        if (levelWords.length === 0) {
            alert('该级别暂无单词，请先添加单词数据');
            return;
        }

        // 生成练习
        this.state.exercises = levelModule.generateExercises(levelWords, 10);
        this.state.levelModule = levelModule;

        // 显示练习屏幕
        this.showScreen('practice');

        // 显示第一题
        this.showExercise();
    },

    /**
     * 显示当前练习
     */
    showExercise() {
        const exercise = this.state.exercises[this.state.currentExerciseIndex];
        const container = document.getElementById('question-container');

        // 更新进度
        document.getElementById('current-question').textContent = this.state.currentExerciseIndex + 1;
        document.getElementById('total-questions').textContent = this.state.exercises.length;
        const progress = ((this.state.currentExerciseIndex + 1) / this.state.exercises.length) * 100;
        document.getElementById('progress-fill').style.width = `${progress}%`;

        this.state.isAnswered = false;

        // 根据练习类型渲染
        let html = '';

        switch (exercise.type) {
            case 'listen选择题':
                html = this.renderListenQuestion(exercise);
                break;
            case 'word选择题':
                html = this.renderWordQuestion(exercise);
                break;
            case 'sentence填空':
                html = this.renderSentenceFillQuestion(exercise);
                break;
            case 'fill填空':
                html = this.renderFillQuestion(exercise);
                break;
            case 'listen拼写':
                html = this.renderListenSpellingQuestion(exercise);
                break;
            case 'match配对':
                html = this.renderMatchQuestion(exercise);
                break;
            case 'synonym选择题':
                html = this.renderSynonymQuestion(exercise);
                break;
            case 'context阅读':
                html = this.renderContextQuestion(exercise);
                break;
            case 'timer抢答':
                html = this.renderTimerQuestion(exercise);
                break;
            default:
                html = this.renderWordQuestion(exercise);
        }

        container.innerHTML = html;

        // 绑定答案事件
        this.bindAnswerEvents();

        // 播放音频（如果有）
        if (exercise.audio) {
            setTimeout(() => {
                TTS.speakWord(exercise.word);
            }, 500);
        }

        // 启动计时器（如果是计时题）
        if (exercise.type === 'timer抢答') {
            this.startTimer(exercise.timeLimit);
        }
    },

    /**
     * 渲染图片选择题
     */
    renderImageQuestion(exercise) {
        // 使用本地 SVG 图片
        const imageUrl = exercise.image || `assets/${exercise.word.toLowerCase()}.svg`;

        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <img class="question-image" src="${imageUrl}" alt="${exercise.word}"
                     style="max-width: 100%; max-height: 180px; border-radius: 12px; margin-bottom: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <button class="audio-btn" onclick="APP.playAudio('${exercise.word}')">&#128266; 播放发音</button>
                <div class="question-hint">请选择这个图片对应的英文单词</div>
                <div class="answer-options">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染听音选择题
     */
    renderListenQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <button class="audio-btn" onclick="APP.playAudio('${exercise.word}')">🔊 点击听发音</button>
                <div class="question-hint">请选择你听到的单词含义</div>
                <div class="answer-options">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染单词选择题
     */
    renderWordQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <div class="question-word">${exercise.word}</div>
                <button class="audio-btn" onclick="APP.playAudio('${exercise.word}')">🔊 播放发音</button>
                <div class="question-hint">请选择正确的中文含义</div>
                <div class="answer-options">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染句子填空题
     */
    renderSentenceFillQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <div class="question-sentence" style="
                    background: linear-gradient(135deg, #6c5ce7, #a29bfe);
                    color: white;
                    padding: 20px;
                    border-radius: 12px;
                    font-size: 18px;
                    line-height: 1.8;
                    margin-bottom: 20px;
                    text-align: center;
                ">${exercise.sentence}</div>
                <div class="question-hint">请选择正确的单词填入空白处</div>
                <div class="answer-options" style="grid-template-columns: repeat(2, 1fr);">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染填空题
     */
    renderFillQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <div class="question-sentence">${exercise.sentence}</div>
                <div class="question-hint">提示: ${exercise.hint}</div>
                <div class="answer-options">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染听音拼写题
     */
    renderListenSpellingQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <div style="margin: 20px 0;">
                    <button class="audio-btn" onclick="APP.playAudio('${exercise.word}')" style="font-size: 18px; padding: 16px 32px;">
                        🔊 点击听发音
                    </button>
                    <button class="audio-btn" onclick="APP.playAudio('${exercise.word}')" style="background: #a29bfe; margin-left: 10px;">
                        🔄 重复听
                    </button>
                </div>
                <div class="question-hint">${exercise.hint || '输入你听到的单词拼写'}</div>
                <input type="text" class="answer-input" id="spelling-input" placeholder="在这里输入单词拼写" autocomplete="off" style="font-size: 20px; padding: 16px;">
                <button class="submit-btn" id="submit-spelling" style="margin-top: 16px;">确认答案</button>
            </div>
        `;
    },

    /**
     * 渲染配对题
     */
    renderMatchQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <div class="question-word" style="font-size:24px; margin-bottom:20px;">${exercise.word}</div>
                <div class="question-hint">请选择正确的英文翻译</div>
                <div class="answer-options">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染同义词选择题
     */
    renderSynonymQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <div class="question-word">${exercise.word}</div>
                <button class="audio-btn" onclick="APP.playAudio('${exercise.word}')">🔊 播放发音</button>
                <div class="question-hint">请选择意思最相近的单词</div>
                <div class="answer-options">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染阅读理解题
     */
    renderContextQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">${this.state.levelModule.getExerciseDescription(exercise.type)}</div>
                <div class="question-context" style="background:#f0f0f0; padding:16px; border-radius:8px; margin-bottom:16px; text-align:left; line-height:1.6;">
                    ${exercise.context}
                </div>
                <button class="audio-btn" onclick="APP.playAudio('${exercise.word}')">🔊 播放目标单词</button>
                <div class="question-hint">${exercise.question}</div>
                <div class="answer-options">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染计时抢答题
     */
    renderTimerQuestion(exercise) {
        return `
            <div class="question-container">
                <div class="question-type">⏱️ 计时挑战</div>
                <div class="timer" id="timer-display">剩余时间: <span id="time-remaining">${exercise.timeLimit}</span>秒</div>
                <div class="question-word">${exercise.word}</div>
                <button class="audio-btn" onclick="APP.playAudio('${exercise.word}')">🔊 播放发音</button>
                <div class="question-hint">快速选择正确含义！</div>
                <div class="answer-options">
                    ${exercise.options.map(opt => `<button class="answer-option" data-answer="${opt}">${opt}</button>`).join('')}
                </div>
            </div>
        `;
    },

    /**
     * 绑定答案事件
     */
    bindAnswerEvents() {
        // 选择题选项
        document.querySelectorAll('.answer-option').forEach(option => {
            option.addEventListener('click', () => {
                if (this.state.isAnswered) return;

                const answer = option.dataset.answer;
                this.checkAnswer(answer);
            });
        });

        // 拼写题提交
        const submitBtn = document.getElementById('submit-spelling');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                if (this.state.isAnswered) return;

                const input = document.getElementById('spelling-input');
                const answer = input.value.trim();
                if (answer) {
                    this.checkAnswer(answer);
                }
            });
        }

        // 拼写题回车提交
        const spellingInput = document.getElementById('spelling-input');
        if (spellingInput) {
            spellingInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !this.state.isAnswered) {
                    const answer = spellingInput.value.trim();
                    if (answer) {
                        this.checkAnswer(answer);
                    }
                }
            });
        }
    },

    /**
     * 检查答案
     */
    checkAnswer(answer) {
        if (this.state.isAnswered) return;

        this.state.isAnswered = true;
        const exercise = this.state.exercises[this.state.currentExerciseIndex];
        const result = this.state.levelModule.checkAnswer(exercise, answer);

        // 停止计时器
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }

        // 更新计数
        if (result.correct) {
            this.state.correctCount++;
        } else {
            this.state.wrongCount++;
        }

        // 显示结果样式
        this.showAnswerResult(exercise, answer, result);

        // 更新单词进度
        this.updateWordProgress(exercise, result.correct);

        // 更新连胜
        if (result.correct) {
            this.state.streak++;
        } else {
            this.state.streak = 0;
            this.updateHearts(-1);
        }

        // 延迟后进入下一题
        setTimeout(() => {
            this.nextExercise();
        }, 1500);
    },

    /**
     * 显示答案结果
     */
    showAnswerResult(exercise, answer, result) {
        // 高亮正确答案
        document.querySelectorAll('.answer-option').forEach(option => {
            if (option.dataset.answer === result.correctAnswer) {
                option.classList.add('correct');
            } else if (option.dataset.answer === answer && !result.correct) {
                option.classList.add('wrong');
            }
            option.style.pointerEvents = 'none';
        });

        // 输入框样式
        const input = document.getElementById('spelling-input');
        if (input) {
            input.disabled = true;
            input.classList.add(result.correct ? 'correct' : 'wrong');
        }

        // 显示反馈
        const container = document.querySelector('.question-container');
        const feedback = document.createElement('div');
        feedback.className = `feedback ${result.correct ? 'correct' : 'wrong'}`;
        feedback.style.cssText = `margin-top:20px; padding:12px; border-radius:8px; font-weight:600;`;
        feedback.style.background = result.correct ? '#d4edda' : '#f8d7da';
        feedback.style.color = result.correct ? '#155724' : '#721c24';
        feedback.textContent = result.feedback;
        container.appendChild(feedback);
    },

    /**
     * 更新单词进度
     */
    updateWordProgress(exercise, correct) {
        const progress = Storage.getWordProgressById(exercise.id) || {
            wordId: exercise.id,
            strength: 0,
            correctStreak: 0,
            nextReview: null,
            timesCorrect: 0,
            timesWrong: 0
        };

        // 更新统计
        if (correct) {
            progress.timesCorrect++;
            progress.correctStreak++;
        } else {
            progress.timesWrong++;
            progress.correctStreak = 0;
        }

        // 计算新强度
        progress.strength = SRS.calculateStrength(progress.strength, correct, progress.correctStreak);

        // 计算下次复习时间
        progress.nextReview = SRS.calculateNextReview(progress.strength, correct);

        // 保存
        Storage.updateWordProgress(exercise.id, progress);

        // 更新用户学习的单词列表
        const userData = Storage.getUserData();
        if (!userData.wordsLearned.includes(exercise.id)) {
            userData.wordsLearned.push(exercise.id);
        }
        Storage.setUserData(userData);
    },

    /**
     * 更新生命值
     */
    updateHearts(change) {
        const userData = Storage.getUserData();
        userData.hearts = Math.max(0, Math.min(5, userData.hearts + change));
        Storage.setUserData(userData);
        this.updateUI();
    },

    /**
     * 更新 XP
     */
    updateXP(amount) {
        const userData = Storage.getUserData();
        userData.totalXp += amount;

        // 检查连胜奖励
        const today = new Date().toISOString().split('T')[0];
        if (!userData.streakDates.includes(today)) {
            userData.streakDates.push(today);

            // 更新连胜
            const lastDate = userData.streakDates.length > 1 ? userData.streakDates[userData.streakDates.length - 2] : null;
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            const yesterdayStr = yesterday.toISOString().split('T')[0];

            if (lastDate === yesterdayStr || userData.streakDates.length === 1) {
                userData.streak++;
            } else {
                userData.streak = 1;
            }
        }

        Storage.setUserData(userData);
        this.updateUI();
    },

    /**
     * 下一题
     */
    nextExercise() {
        this.state.currentExerciseIndex++;

        if (this.state.currentExerciseIndex >= this.state.exercises.length) {
            // 练习完成
            this.showResults();
        } else {
            this.showExercise();
        }
    },

    /**
     * 显示结果
     */
    showResults() {
        const total = this.state.exercises.length;
        const correct = this.state.correctCount;
        const wrong = this.state.wrongCount;

        // 计算奖励
        let xpEarned = correct * 10;
        if (correct === total) {
            xpEarned += 10; // 完美奖励
        }

        // 更新 XP
        this.updateXP(xpEarned);

        // 检查成就
        this.checkAchievements();

        // 显示结果屏幕
        document.getElementById('correct-count').textContent = correct;
        document.getElementById('wrong-count').textContent = wrong;
        document.getElementById('xp-earned-value').textContent = `+${xpEarned} XP`;

        // 等级提升检查（简化版：每200XP升一级）
        const userData = Storage.getUserData();
        const newLevel = Math.floor(userData.totalXp / 200) + 1;
        if (newLevel > this.state.currentLevel) {
            document.getElementById('level-up-notification').style.display = 'block';
        } else {
            document.getElementById('level-up-notification').style.display = 'none';
        }

        this.showScreen('results');
    },

    /**
     * 检查成就
     */
    checkAchievements() {
        const userData = Storage.getUserData();
        const progress = Storage.getWordProgress();
        const stats = Storage.getStats();

        const achievements = [
            { id: 'first_lesson', name: '初学者', icon: '🎯', condition: () => stats.totalWordsLearned >= 1 },
            { id: '5_day_streak', name: '5天连胜', icon: '🔥', condition: () => stats.streak >= 5 },
            { id: '30_day_streak', name: '30天连胜', icon: '⭐', condition: () => stats.streak >= 30 },
            { id: '50_words', name: '词汇量50', icon: '📚', condition: () => stats.totalWordsLearned >= 50 },
            { id: '200_words', name: '词汇量200', icon: '📖', condition: () => stats.totalWordsLearned >= 200 },
            { id: 'perfect_score', name: '满分达人', icon: '💯', condition: () => this.state.correctCount === 5 }
        ];

        for (const ach of achievements) {
            if (!userData.achievements.includes(ach.id) && ach.condition()) {
                userData.achievements.push(ach.id);
            }
        }

        Storage.setUserData(userData);
    },

    /**
     * 开始复习
     */
    startReview() {
        // 获取需要复习的单词
        const progressMap = Storage.getWordProgress();
        const reviewWords = SRS.getReviewQueue(this.words, progressMap, 5);

        if (reviewWords.length === 0) {
            alert('暂无需要复习的单词');
            return;
        }

        this.state.currentLevel = 1; // 复习用入门级别
        this.state.correctCount = 0;
        this.state.wrongCount = 0;
        this.state.currentExerciseIndex = 0;
        this.state.exercises = reviewWords.map(w => ({
            id: w.id,
            word: w.word,
            meaning: w.meaning,
            level: w.level || 1,
            type: 'word选择题',
            options: BeginnerLevel.generateMeaningOptions(w, 4),
            correctAnswer: w.meaning
        }));
        this.state.levelModule = BeginnerLevel;

        this.showScreen('practice');
        this.showExercise();
    },

    /**
     * 播放音频
     */
    playAudio(word) {
        const settings = Storage.getSettings();
        TTS.speakWord(word, { speed: settings.ttsSpeed });
    },

    /**
     * 启动计时器
     */
    startTimer(seconds) {
        let remaining = seconds;
        const display = document.getElementById('time-remaining');

        if (display) {
            display.textContent = remaining;
        }

        this.timerInterval = setInterval(() => {
            remaining--;
            if (display) {
                display.textContent = remaining;
            }

            if (remaining <= 0) {
                clearInterval(this.timerInterval);
                // 时间到，自动提交
                if (!this.state.isAnswered) {
                    this.state.isAnswered = true;
                    // 选择第一个选项作为答案（随机选择会有惩罚）
                    const firstOption = document.querySelector('.answer-option');
                    if (firstOption) {
                        // 不给出答案，算错
                        this.updateHearts(-1);
                        this.state.wrongCount++;
                        this.state.streak = 0;

                        // 显示超时提示
                        const container = document.querySelector('.question-container');
                        const feedback = document.createElement('div');
                        feedback.className = 'feedback wrong';
                        feedback.style.cssText = `margin-top:20px; padding:12px; border-radius:8px; font-weight:600; background:#f8d7da; color:#721c24;`;
                        feedback.textContent = '时间到！';
                        container.appendChild(feedback);

                        setTimeout(() => {
                            this.nextExercise();
                        }, 1500);
                    }
                }
            }
        }, 1000);
    },

    /**
     * 更新 UI
     */
    updateUI() {
        const userData = Storage.getUserData();
        const stats = Storage.getStats();

        // 更新头部
        document.getElementById('xp-display').textContent = `${userData.totalXp} XP`;
        document.getElementById('streak-display').textContent = userData.streak;

        // 更新心形
        const hearts = '❤'.repeat(userData.hearts) + '🖤'.repeat(5 - userData.hearts);
        document.getElementById('hearts-display').textContent = hearts;

        // 更新欢迎页统计
        document.getElementById('total-words').textContent = stats.totalWordsLearned;
        document.getElementById('total-days').textContent = userData.streakDates ? userData.streakDates.length : 0;
        document.getElementById('achievement-count').textContent = userData.achievements.length;
    },

    /**
     * 更新统计屏幕
     */
    updateStatsScreen() {
        const stats = Storage.getStats();
        const userData = Storage.getUserData();

        // 成就列表
        const allAchievements = [
            { id: 'first_lesson', name: '初学者', icon: '🎯' },
            { id: '5_day_streak', name: '5天连胜', icon: '🔥' },
            { id: '30_day_streak', name: '30天连胜', icon: '⭐' },
            { id: '50_words', name: '词汇量50', icon: '📚' },
            { id: '200_words', name: '词汇量200', icon: '📖' },
            { id: 'perfect_score', name: '满分达人', icon: '💯' }
        ];

        const achievementList = document.getElementById('achievement-list');
        achievementList.innerHTML = allAchievements.map(ach => {
            const unlocked = userData.achievements.includes(ach.id);
            return `
                <div class="achievement-item ${unlocked ? 'unlocked' : ''}">
                    <div class="achievement-icon">${ach.icon}</div>
                    <div class="achievement-name">${ach.name}</div>
                </div>
            `;
        }).join('');

        // 日历热力图（简化版）
        const calendarGrid = document.getElementById('calendar-grid');
        const today = new Date();
        const days = [];

        for (let i = 27; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split('T')[0];
            const isActive = userData.streakDates && userData.streakDates.includes(dateStr);
            const isToday = i === 0;

            days.push(`<div class="calendar-day ${isActive ? 'active' : ''} ${isToday ? 'today' : ''}">${date.getDate()}</div>`);
        }

        calendarGrid.innerHTML = days.join('');

        // 进度图表（简化柱状图）
        const progressChart = document.getElementById('progress-chart');
        const progressData = [
            stats.masteredWords,
            stats.learningWords,
            Math.max(0, 30 - stats.totalWordsLearned)
        ];

        progressChart.innerHTML = progressData.map((value, index) => {
            const height = Math.max(10, (value / 30) * 100);
            const colors = ['#00b894', '#fdcb6e', '#e0e0e0'];
            return `<div class="progress-bar-item" style="height:${height}%; background:${colors[index]};"></div>`;
        }).join('');
    }
};

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    APP.init();
    window.APP = APP; // 暴露到全局
});
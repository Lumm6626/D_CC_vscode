/**
 * Basic English — 主控制器
 * 5 步学习流程：操作词 → 事物词 → 属性词 → 转述 → 阅读
 */

const APP = {
    currentStep: 1,
    currentSubStep: null, // 'things' | 'qualities' for step 2-3
    exercises: [],
    exerciseIndex: 0,
    correctCount: 0,
    wrongCount: 0,
    wrongAnswers: [],
    inPractice: false,
    readingActive: false,

    /**
     * 初始化应用
     */
    async init() {
        TTS.init();

        // 加载数据
        if (window.BASIC_WORDS) {
            OperationsEngine.init(window.BASIC_WORDS);
            VocabularyEngine.init(window.BASIC_WORDS);
            BasicChecker.init(window.BASIC_WORDS);
            Storage.setWordCache(window.BASIC_WORDS);
        } else {
            // 尝试从缓存加载
            const cached = Storage.getWordCache();
            if (cached) {
                OperationsEngine.init(cached);
                VocabularyEngine.init(cached);
                BasicChecker.init(cached);
            }
        }

        if (window.PARAPHRASING_EXAMPLES) {
            ParaphrasingEngine.init(window.PARAPHRASING_EXAMPLES, window.BASIC_WORDS || []);
        }

        if (window.READING_PASSAGES) {
            ReadingEngine.init(window.READING_PASSAGES);
        }

        // 每日检查
        Storage.checkDailyReset();

        // 检查步骤解锁
        this._checkUnlocks();

        // 获取当前步骤
        const userData = Storage.getUserData();
        this.currentStep = userData.currentStep || 1;

        // 渲染界面
        this._renderHomeScreen();
        this._updateStepIndicator();
        this._updateNav();
        this._bindEvents();
    },

    /**
     * 检查各步骤解锁条件
     */
    _checkUnlocks() {
        const userData = Storage.getUserData();
        const progressMap = Storage.getWordProgress();

        const opsScore = OperationsEngine.getScore();
        const vocabScore = VocabularyEngine.getScore('all');
        const thingsScore = VocabularyEngine.getScore('things');

        // Step 2: 学会 80/100 操作词 (strength >= 2)
        const opsLearned = opsScore.total > 0
            ? Object.values(progressMap).filter((p, i) => {
                const w = window.BASIC_WORDS?.find(w => w.id === p.wordId);
                return w && w.type === 'operation' && p.strength >= 2;
            }).length
            : 0;

        // Step 3: 学会 50 个事物词
        const thingsLearned = thingsScore.total > 0
            ? Object.values(progressMap).filter((p, i) => {
                const w = window.BASIC_WORDS?.find(w => w.id === p.wordId);
                return w && w.type === 'thing' && p.strength >= 2;
            }).length
            : 0;

        // Step 4: 学会 200+ 词汇 (strength >= 2)
        const totalLearned = Object.values(progressMap).filter(p => p.strength >= 2).length;

        // Step 5: 完成 10 次转述练习
        const paraStats = ParaphrasingEngine.getStats();

        userData.stepUnlocks = userData.stepUnlocks || { step1: true, step2: false, step3: false, step4: false, step5: false };
        userData.stepUnlocks.step1 = true;
        userData.stepUnlocks.step2 = opsLearned >= 50; // 降低门槛方便测试
        userData.stepUnlocks.step3 = thingsLearned >= 20;
        userData.stepUnlocks.step4 = totalLearned >= 50;
        userData.stepUnlocks.step5 = paraStats.total >= 5;

        Storage.setUserData(userData);
    },

    /**
     * 渲染首页
     */
    _renderHomeScreen() {
        const stats = Storage.getStats();
        const userData = Storage.getUserData();

        // 问候语
        const greetingText = document.getElementById('greeting-text');
        const greetingDetail = document.getElementById('greeting-detail');
        const hour = new Date().getHours();
        const timeGreeting = hour < 12 ? '早安' : hour < 18 ? '下午好' : '晚安';

        const reviewCount = this._getReviewCount();
        greetingText.textContent = `${timeGreeting}，欢迎回来`;
        if (reviewCount > 0) {
            greetingDetail.textContent = `今天有 ${reviewCount} 个词需要复习`;
        } else {
            greetingDetail.textContent = '准备开始今天的练习吧';
        }

        // 统计数字
        document.getElementById('stat-mastered').textContent = stats.masteredWords;
        document.getElementById('stat-learning').textContent = stats.learningWords;
        document.getElementById('stat-streak').textContent = stats.streak;

        // 步骤卡片
        const stepCards = document.getElementById('step-cards');
        const steps = [
            { id: 1, title: '操作词', sub: '100 个核心词', desc: 'come, get, give, go... 英语的"动词引擎"' },
            { id: 2, title: '事物词', sub: '600 个名词', desc: '日常生活中的一切事物' },
            { id: 3, title: '属性词', sub: '150 个形容词', desc: '描述世界的颜色和形状' },
            { id: 4, title: '转述练习', sub: '核心训练', desc: '用 850 词改写任何复杂表达' },
            { id: 5, title: '阅读理解', sub: '综合应用', desc: '读纯 Basic English 文章' }
        ];

        stepCards.innerHTML = '';
        for (const step of steps) {
            const unlocked = userData.stepUnlocks ? userData.stepUnlocks[`step${step.id}`] : step.id === 1;
            const card = document.createElement('button');
            card.className = `option-btn ${!unlocked ? 'dimmed' : ''}`;
            card.style.display = 'flex';
            card.style.flexDirection = 'column';
            card.style.alignItems = 'flex-start';
            card.style.gap = '4px';
            card.style.textAlign = 'left';
            card.style.padding = 'var(--space-lg)';

            card.innerHTML = `
                <span style="font-family:var(--font-display);font-size:var(--text-title);font-weight:700;color:${unlocked ? 'var(--ink)' : 'var(--ink-faint)'};">${step.title}</span>
                <span style="font-size:var(--text-caption);color:var(--ink-faint);">${step.sub}</span>
                <span style="font-size:var(--text-small);color:var(--ink-light);">${step.desc}</span>
                ${!unlocked ? `<span style="font-size:var(--text-caption);color:var(--ink-faint);margin-top:4px;">🔒 未解锁</span>` : ''}
            `;

            if (unlocked) {
                card.addEventListener('click', () => this._startStep(step.id));
            } else {
                card.addEventListener('click', () => {
                    const messages = {
                        2: `需要掌握 ${Math.max(0, 50 - this._countLearned('operation'))} 个以上的操作词才能解锁`,
                        3: '需要先学习事物词才能解锁属性词',
                        4: '需要掌握 200+ 词汇才能解锁转述练习',
                        5: '需要完成 10 次转述练习才能解锁阅读'
                    };
                    this._showToast(messages[step.id] || '尚未解锁');
                });
            }

            stepCards.appendChild(card);
        }
    },

    _countLearned(type) {
        const progressMap = Storage.getWordProgress();
        return Object.values(progressMap).filter(p => {
            const w = window.BASIC_WORDS?.find(w => w.id === p.wordId);
            return w && w.type === type && p.strength >= 2;
        }).length;
    },

    _getReviewCount() {
        const words = window.BASIC_WORDS || Storage.getWordCache() || [];
        const progressMap = Storage.getWordProgress();
        const reviewQueue = SRS.getReviewQueue(words, progressMap, 100);
        return reviewQueue.length;
    },

    /**
     * 开始一个学习步骤
     */
    _startStep(stepId) {
        this.currentStep = stepId;
        this.correctCount = 0;
        this.wrongCount = 0;
        this.wrongAnswers = [];
        this.exerciseIndex = 0;

        switch (stepId) {
            case 1:
                this.exercises = OperationsEngine.generateExercises(10);
                break;
            case 2:
                this.currentSubStep = 'things';
                this.exercises = VocabularyEngine.generateExercises('things', 10);
                break;
            case 3:
                this.currentSubStep = 'qualities';
                this.exercises = VocabularyEngine.generateExercises('qualities', 10);
                break;
            case 4:
                this.exercises = ParaphrasingEngine.generateExercises(10);
                break;
            case 5:
                this._startReading();
                return;
        }

        if (this.exercises.length === 0) {
            this._showToast('暂无练习数据，请检查数据文件');
            return;
        }

        this.inPractice = true;
        this.readingActive = false;
        this._showScreen('practice-screen');
        this._renderExercise();
    },

    /**
     * 开始阅读
     */
    _startReading() {
        const passage = ReadingEngine.getRecommendedPassage();
        if (!passage) {
            this._showToast('暂无阅读文章');
            return;
        }

        this.readingActive = true;
        this.inPractice = false;
        ReadingEngine.startPassage(passage);

        this._showScreen('reading-screen');
        this._renderReading();
    },

    /**
     * 渲染当前练习
     */
    _renderExercise() {
        if (this.exerciseIndex >= this.exercises.length) {
            this._showResults();
            return;
        }

        const exercise = this.exercises[this.exerciseIndex];
        const progressText = document.getElementById('practice-progress');
        progressText.textContent = `${this.exerciseIndex + 1} / ${this.exercises.length}`;

        // 隐藏所有模式区域
        const wordCard = document.getElementById('word-card');
        const questionPrompt = document.getElementById('question-prompt');
        const answerOptions = document.getElementById('answer-options');
        const paraphraseArea = document.getElementById('paraphrase-area');
        const btnNext = document.getElementById('btn-next');

        wordCard.classList.remove('correct-answer', 'wrong-answer');
        wordCard.style.display = 'block';
        questionPrompt.style.display = 'block';
        answerOptions.style.display = 'grid';
        paraphraseArea.classList.add('hidden');
        btnNext.classList.add('hidden');

        // 渲染单词卡片 — 不含任何答案提示
        document.getElementById('card-phonetic').textContent = exercise.phonetic || '';
        document.getElementById('card-word').textContent = exercise.word;
        document.getElementById('card-chinese').textContent = exercise.chinese || '';

        const audioBtn = document.getElementById('card-audio-btn');
        audioBtn.onclick = () => TTS.speakWord(exercise.word);

        // 清理残留的搭配提示
        const existingCombos = document.getElementById('word-combos-inline');
        if (existingCombos) existingCombos.remove();

        // 根据题型渲染
        questionPrompt.textContent = exercise.question || '';

        switch (exercise.mode || exercise.displayType) {
            case 'meaning':
            case 'picture':
            case 'antonym':
            case 'context':
                this._renderOptions(exercise);
                break;

            case 'combination':
                this._renderCombinationOptions(exercise);
                break;

            case 'identification':
                this._renderIdentificationOptions(exercise);
                break;

            case 'choice':
                this._renderParaChoiceOptions(exercise);
                break;

            case 'identify':
                this._renderIdentifyNonBasic(exercise);
                break;

            case 'free_input':
                this._renderFreeInput(exercise);
                break;

            default:
                if (exercise.options) {
                    this._renderOptions(exercise);
                } else if (exercise.comboOptions) {
                    this._renderCombinationOptions(exercise);
                }
                break;
        }
    },

    _renderOptions(exercise) {
        const container = document.getElementById('answer-options');
        container.style.display = 'grid';
        container.innerHTML = '';

        const options = exercise.options || [];
        for (const opt of options) {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.innerHTML = `<span>${opt.chinese}</span>`;
            btn.addEventListener('click', () => {
                this._handleAnswer(exercise, opt.word, btn, container);
            });
            container.appendChild(btn);
        }

        // 如果是语境题，先展示句子
        if (exercise.contextSentence) {
            const promptEl = document.getElementById('question-prompt');
            promptEl.innerHTML = `<span style="font-family:var(--font-display);font-style:italic;color:var(--ink);">"${exercise.contextSentence}"</span>`;
        }
    },

    _renderCombinationOptions(exercise) {
        // 隐藏标准选项区，使用独立的 combination 布局
        const answerOptions = document.getElementById('answer-options');
        answerOptions.style.display = 'none';

        // 先渲染 Replacement Showcase（核心视觉）
        const questionPrompt = document.getElementById('question-prompt');
        questionPrompt.innerHTML = '';

        // 在 word card 下方插入 replacement showcase
        const wordCard = document.getElementById('word-card');

        // 移除旧的 showcase
        const existingShowcase = document.getElementById('replacement-showcase');
        if (existingShowcase) existingShowcase.remove();

        const showcase = document.createElement('div');
        showcase.id = 'replacement-showcase';
        showcase.className = 'replacement-showcase';

        const targetReplace = exercise.replaces[0];
        showcase.innerHTML = `
            <div class="rs-label">用 Basic English 替代</div>
            <div class="rs-complex">${targetReplace}</div>
            <div class="rs-arrow">↓</div>
            <div class="rs-verb">${exercise.verb} <span class="rs-particle">?</span></div>
        `;

        wordCard.after(showcase);

        // 在 showcase 下渲染组合选项
        const comboContainer = document.createElement('div');
        comboContainer.id = 'combination-options';
        comboContainer.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px;';

        // 移除旧的
        const existingComboOpts = document.getElementById('combination-options');
        if (existingComboOpts) existingComboOpts.remove();

        const options = exercise.comboOptions || [];
        for (const opt of options) {
            const btn = document.createElement('button');
            btn.className = 'combination-option';
            btn.innerHTML = `
                <span class="co-verb">${opt.verb}</span>
                <span class="co-particle">${opt.particle}</span>
            `;
            btn.addEventListener('click', () => {
                this._handleCombinationAnswer(exercise, opt, btn, comboContainer, showcase);
            });
            comboContainer.appendChild(btn);
        }

        showcase.after(comboContainer);
    },

    _handleCombinationAnswer(exercise, answer, clickedBtn, container, showcase) {
        const allBtns = container.querySelectorAll('button');
        allBtns.forEach(b => b.disabled = true);

        const result = OperationsEngine.checkAnswer(exercise, answer);
        const correctOpt = exercise.comboOptions.find(o => o.correct);
        const correctParticle = correctOpt ? correctOpt.particle : exercise.correctParticle;

        if (result.correct) {
            this.correctCount++;
            clickedBtn.classList.add('correct');
            document.getElementById('word-card').classList.add('correct-answer');
            const particleSpan = showcase.querySelector('.rs-particle');
            if (particleSpan) {
                particleSpan.textContent = answer.particle;
                particleSpan.style.color = 'var(--success)';
                particleSpan.style.background = 'var(--success-soft)';
            }
        } else {
            this.wrongCount++;
            this._trackWrongAnswer(exercise, answer.particle, correctParticle);
            clickedBtn.classList.add('wrong');
            document.getElementById('word-card').classList.add('wrong-answer');

            Array.from(allBtns).forEach(b => {
                const pSpan = b.querySelector('.co-particle');
                if (pSpan && pSpan.textContent === correctParticle) {
                    b.classList.add('correct');
                } else if (b !== clickedBtn) {
                    b.classList.add('dimmed');
                }
            });

            const particleSpan = showcase.querySelector('.rs-particle');
            if (particleSpan) {
                particleSpan.textContent = correctParticle;
                particleSpan.style.color = 'var(--error)';
                particleSpan.style.background = 'var(--error-soft)';
            }
        }

        // 解答区：显示完整的替换关系 + 例句
        const explanationDiv = document.createElement('div');
        explanationDiv.style.cssText = 'margin-top:16px;padding:20px;background:var(--paper-dark);border-radius:12px;text-align:center;';
        explanationDiv.innerHTML = `
            <div style="font-size:var(--text-caption);color:var(--ink-faint);margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">替换关系</div>
            <div style="font-family:var(--font-display);font-size:20px;color:var(--ink-light);text-decoration:line-through;margin-bottom:4px;">${exercise.replaces.join(', ')}</div>
            <div style="color:var(--accent);font-size:20px;margin-bottom:4px;">↓</div>
            <div style="font-family:var(--font-display);font-size:24px;font-weight:700;color:var(--ink);">${exercise.verb} <span style="color:var(--accent);">${correctParticle}</span></div>
            ${correctOpt && correctOpt.example ? `<div style="font-family:var(--font-display);font-style:italic;font-size:var(--text-body);color:var(--ink);margin-top:12px;padding-top:12px;border-top:1px solid var(--divider);">"${correctOpt.example}"</div>` : ''}
        `;
        container.after(explanationDiv);

        // 反馈文字
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = result.correct ? 'checker-feedback valid' : 'checker-feedback invalid';
        feedbackDiv.style.marginTop = '12px';
        feedbackDiv.innerHTML = `<div class="feedback-title">${result.feedback}</div>`;
        explanationDiv.after(feedbackDiv);

        // 显示"下一题"
        const btnNext = document.getElementById('btn-next');
        btnNext.classList.remove('hidden');
        btnNext.onclick = () => {
            // 清理 combination 特有元素
            const showcase = document.getElementById('replacement-showcase');
            const comboOpts = document.getElementById('combination-options');
            if (showcase) showcase.remove();
            if (comboOpts) comboOpts.remove();
            if (explanationDiv) explanationDiv.remove();
            if (feedbackDiv) feedbackDiv.remove();
            document.getElementById('answer-options').style.display = 'grid';

            this.exerciseIndex++;
            if (this.exerciseIndex >= this.exercises.length) {
                this._showResults();
            } else {
                this._renderExercise();
            }
        };
    },

    _renderIdentificationOptions(exercise) {
        const container = document.getElementById('answer-options');
        container.style.display = 'grid';
        container.innerHTML = '';

        const options = exercise.idOptions || [];
        const selected = new Set();

        // 添加确认按钮
        const confirmRow = document.createElement('div');
        confirmRow.style.cssText = 'grid-column: 1 / -1; text-align: center;';
        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'option-btn';
        confirmBtn.style.cssText = 'width: 100%;';
        confirmBtn.textContent = '确认选择';
        confirmBtn.addEventListener('click', () => {
            const selectedIndices = Array.from(selected);
            this._handleAnswer(exercise, selectedIndices, confirmBtn, container);
        });

        for (const opt of options) {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.innerHTML = `<span style="font-family:var(--font-display);font-size:var(--text-body);">${opt.word}</span>`;
            btn.addEventListener('click', () => {
                if (selected.has(opt.word)) {
                    selected.delete(opt.word);
                    btn.style.borderColor = 'transparent';
                    btn.style.background = 'var(--paper-dark)';
                } else {
                    selected.add(opt.word);
                    btn.style.borderColor = 'var(--accent)';
                    btn.style.background = 'var(--accent-soft)';
                }
            });
            container.appendChild(btn);
        }

        confirmRow.appendChild(confirmBtn);
        container.appendChild(confirmRow);
    },

    _renderParaChoiceOptions(exercise) {
        const container = document.getElementById('answer-options');
        container.style.display = 'grid';
        container.style.gridTemplateColumns = '1fr';
        container.innerHTML = '';

        document.getElementById('question-prompt').innerHTML = `
            <span style="color:var(--ink-light);">将以下句子改写为 Basic English：</span><br>
            <span style="font-family:var(--font-display);font-style:italic;font-size:var(--text-body);color:var(--ink);margin-top:8px;display:inline-block;">"${exercise.normal}"</span>
        `;

        const options = exercise.options || [];
        for (const opt of options) {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.style.textAlign = 'left';
            btn.style.fontFamily = 'var(--font-mono)';
            btn.style.fontSize = 'var(--text-small)';
            btn.innerHTML = `<span>${opt.text}</span>`;
            btn.addEventListener('click', () => {
                this._handleAnswer(exercise, opt, btn, container);
            });
            container.appendChild(btn);
        }
    },

    _renderIdentifyNonBasic(exercise) {
        // 在问题区展示句子，让用户点击识别非 Basic 词
        const container = document.getElementById('answer-options');
        container.style.display = 'grid';
        container.style.gridTemplateColumns = '1fr';
        container.innerHTML = '';

        document.getElementById('question-prompt').textContent = exercise.question;

        // 分词展示，每词可点击
        const wordsDisplay = document.createElement('div');
        wordsDisplay.style.cssText = 'font-family:var(--font-mono);font-size:var(--text-body);line-height:2;padding:var(--space-lg);background:var(--paper-dark);border-radius:var(--radius-md);margin-bottom:var(--space-md);display:flex;flex-wrap:wrap;gap:4px;';
        wordsDisplay.id = 'identify-words-display';

        const tokens = exercise.normal.match(/[a-zA-Z]+/g) || [];
        const selectedTokens = new Set();

        for (const token of tokens) {
            const span = document.createElement('span');
            span.textContent = token;
            span.style.cssText = 'padding:2px 6px;border-radius:4px;cursor:pointer;transition:all 150ms ease;';
            span.addEventListener('click', () => {
                if (selectedTokens.has(token)) {
                    selectedTokens.delete(token);
                    span.style.background = 'transparent';
                    span.style.textDecoration = 'none';
                } else {
                    selectedTokens.add(token);
                    span.style.background = 'var(--error-soft)';
                    span.style.textDecoration = 'underline wavy var(--error)';
                    span.style.textUnderlineOffset = '3px';
                }
            });
            wordsDisplay.appendChild(span);
        }

        container.appendChild(wordsDisplay);

        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'option-btn';
        confirmBtn.textContent = '确认';
        confirmBtn.addEventListener('click', () => {
            this._handleAnswer(exercise, Array.from(selectedTokens), confirmBtn, container);
        });
        container.appendChild(confirmBtn);
    },

    _renderFreeInput(exercise) {
        document.getElementById('question-prompt').innerHTML = `
            <span style="color:var(--ink-light);">将以下句子改写为 Basic English（只用 850 词）：</span><br>
            <span style="font-family:var(--font-display);font-style:italic;font-size:var(--text-body);color:var(--ink);margin-top:8px;display:inline-block;">"${exercise.normal}"</span>
        `;

        const answerOptions = document.getElementById('answer-options');
        answerOptions.style.display = 'none';

        const paraphraseArea = document.getElementById('paraphrase-area');
        paraphraseArea.classList.remove('hidden');

        document.getElementById('paraphrase-original').textContent = exercise.normal;
        const inputEl = document.getElementById('paraphrase-input');
        inputEl.value = '';
        inputEl.focus();

        const feedbackEl = document.getElementById('checker-feedback');
        feedbackEl.style.display = 'none';

        const submitBtn = document.getElementById('paraphrase-submit');
        submitBtn.classList.remove('has-input');
        submitBtn.textContent = '提交检查';

        // 实时输入反馈
        inputEl.oninput = () => {
            const value = inputEl.value.trim();
            if (value.length > 0) {
                submitBtn.classList.add('has-input');
                submitBtn.textContent = '提交检查';

                // 实时 checker 反馈
                if (value.split(/\s+/).length >= 2) {
                    const result = BasicChecker.checkSentence(value);
                    if (result.invalidWords.length > 0) {
                        feedbackEl.style.display = 'block';
                        feedbackEl.className = 'checker-feedback invalid';
                        feedbackEl.innerHTML = `
                            <div class="feedback-title">${result.invalidWords.length} 个词不在 Basic English 中</div>
                            ${result.suggestions.map(s =>
                                `<div class="invalid-word"><span class="original">${s.original}</span><span class="arrow">→</span><span class="suggestion">${s.suggestion}</span></div>`
                            ).join('')}
                        `;
                    } else {
                        feedbackEl.style.display = 'block';
                        feedbackEl.className = 'checker-feedback valid';
                        feedbackEl.innerHTML = `<div class="feedback-title">全部词汇在 Basic English 850 词内</div>`;
                    }
                } else {
                    feedbackEl.style.display = 'none';
                }
            } else {
                submitBtn.classList.remove('has-input');
                submitBtn.textContent = '提交检查';
                feedbackEl.style.display = 'none';
            }
        };

        // 提交按钮
        submitBtn.onclick = () => {
            const answer = inputEl.value.trim();
            if (!answer) return;

            this._handleAnswer(exercise, answer, submitBtn);
        };
    },

    /**
     * 处理用户答案
     */
    _handleAnswer(exercise, answer, clickedBtn, container) {
        // 禁用所有按钮
        const allBtns = container.querySelectorAll('button');
        allBtns.forEach(b => b.disabled = true);

        let engine;
        if (this.currentStep === 1) {
            engine = OperationsEngine;
        } else if (this.currentStep === 2 || this.currentStep === 3) {
            engine = VocabularyEngine;
        } else if (this.currentStep === 4) {
            engine = ParaphrasingEngine;
        }

        const result = engine.checkAnswer(exercise, answer);

        // 视觉反馈
        if (result.correct) {
            this.correctCount++;
            clickedBtn.classList.add('correct');
            document.getElementById('word-card').classList.add('correct-answer');
        } else {
            this.wrongCount++;
            this._trackWrongAnswer(exercise, answer, result.correctAnswer);
            clickedBtn.classList.add('wrong');
            document.getElementById('word-card').classList.add('wrong-answer');

            // 高亮正确答案
            if (exercise.options) {
                const correctOpt = exercise.options.find(o => o.word === result.correctAnswer);
                if (correctOpt) {
                    const correctBtn = Array.from(allBtns).find(b => b.textContent.includes(correctOpt.chinese));
                    if (correctBtn && correctBtn !== clickedBtn) {
                        correctBtn.classList.add('correct');
                    }
                }
            }
            if (exercise.comboOptions) {
                const correctIndex = exercise.correctIndex;
                const btns = Array.from(allBtns).filter(b => !b.textContent.includes('确认'));
                if (correctIndex !== undefined && btns[correctIndex]) {
                    btns[correctIndex].classList.add('correct');
                }
            }

            // 淡化错误选项
            Array.from(allBtns).forEach(b => {
                if (!b.classList.contains('correct') && !b.classList.contains('wrong')) {
                    b.classList.add('dimmed');
                }
            });
        }

        // 显示反馈信息
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = result.correct ? 'checker-feedback valid' : 'checker-feedback invalid';
        feedbackDiv.style.marginTop = 'var(--space-lg)';
        feedbackDiv.innerHTML = `<div class="feedback-title">${result.feedback}</div>`;

        if (result.hint) {
            feedbackDiv.innerHTML += `<div style="font-size:var(--text-caption);margin-top:4px;color:var(--ink-faint);">提示：${result.hint}</div>`;
        }

        container.appendChild(feedbackDiv);

        // 对 free_input 模式，也展示反馈
        if (exercise.mode === 'free_input') {
            const feedbackEl = document.getElementById('checker-feedback');
            if (result.checkerResult && !result.correct) {
                feedbackEl.style.display = 'block';
                feedbackEl.className = 'checker-feedback invalid';
                feedbackEl.innerHTML = `
                    <div class="feedback-title">${result.feedback}</div>
                    <div style="margin-top:8px;font-size:var(--text-small);color:var(--ink-light);">标准答案：${result.correctAnswer}</div>
                `;
            } else if (result.correct) {
                feedbackEl.style.display = 'block';
                feedbackEl.className = 'checker-feedback valid';
                feedbackEl.innerHTML = `<div class="feedback-title">${result.feedback}</div>`;
            }
            document.getElementById('paraphrase-submit').style.display = 'none';
        }

        // 显示"下一题"按钮
        const btnNext = document.getElementById('btn-next');
        btnNext.classList.remove('hidden');
        btnNext.onclick = () => {
            this.exerciseIndex++;
            if (this.exerciseIndex >= this.exercises.length) {
                this._showResults();
            } else {
                this._renderExercise();
            }
        };
    },

    /**
     * 渲染阅读界面
     */
    _renderReading() {
        const passage = ReadingEngine.currentPassage;
        if (!passage) return;

        const passageEl = document.getElementById('reading-passage');
        passageEl.innerHTML = `
            <div class="passage-title">${passage.title}</div>
            ${passage.text.split('\n\n').map(p => `<p style="margin-bottom:var(--space-lg);">${p}</p>`).join('')}
            <div class="passage-source">— ${passage.source}</div>
        `;

        // 词汇注释
        const vocabNotes = document.getElementById('vocab-notes');
        if (passage.vocabulary_notes && passage.vocabulary_notes.length > 0) {
            vocabNotes.classList.remove('hidden');
            vocabNotes.innerHTML = `
                <h4>词汇注释</h4>
                ${passage.vocabulary_notes.map(vn => `
                    <div class="vocab-note-item">
                        <span class="vn-word">${vn.word}</span>
                        <span class="vn-meaning">${vn.meaning}</span>
                    </div>
                `).join('')}
            `;
        } else {
            vocabNotes.classList.add('hidden');
        }

        // 问题
        const questionsEl = document.getElementById('reading-questions');
        questionsEl.innerHTML = '';
        for (let i = 0; i < passage.questions.length; i++) {
            const q = passage.questions[i];
            const card = document.createElement('div');
            card.className = 'reading-question-card';
            card.innerHTML = `
                <div class="question-text">${i + 1}. ${q.question}</div>
                <div class="options-grid" data-question="${i}">
                    ${q.options.map((opt, j) => `
                        <button class="option-btn" data-q="${i}" data-opt="${j}">${opt}</button>
                    `).join('')}
                </div>
            `;
            questionsEl.appendChild(card);

            // 绑定选项点击
            card.querySelectorAll('.option-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const qIdx = parseInt(btn.dataset.q);
                    const optIdx = parseInt(btn.dataset.opt);

                    // 清除同题其他选择
                    const siblings = card.querySelectorAll('.option-btn');
                    siblings.forEach(s => {
                        s.style.borderColor = 'transparent';
                        s.style.background = 'var(--paper)';
                    });

                    // 高亮当前选择
                    btn.style.borderColor = 'var(--accent)';
                    btn.style.background = 'var(--accent-soft)';

                    ReadingEngine.submitAnswer(qIdx, optIdx);
                });
            });
        }

        document.getElementById('btn-submit-reading').onclick = () => {
            this._showReadingResults();
        };
    },

    _showReadingResults() {
        const results = ReadingEngine.getResults();
        if (!results) return;

        this._showScreen('results-screen');

        const userData = Storage.getUserData();
        const xpEarned = results.correctCount * 10;
        userData.totalXp = (userData.totalXp || 0) + xpEarned;
        Storage.setUserData(userData);

        document.getElementById('result-mastered').textContent = `${results.score}%`;
        document.getElementById('result-message').innerHTML = `
            ${results.correctCount}/${results.totalQuestions} 题正确<br>
            <span style="font-size:var(--text-small);color:var(--ink-faint);">阅读理解完成 · +${xpEarned} XP</span>
            ${results.score === 100
                ? '<br><span style="color:var(--success);">完美！你对 Basic English 的理解非常好。</span>'
                : '<br><span style="color:var(--ink-light);">慢慢来，阅读理解需要时间积累。</span>'}
            ${results.vocabularyNotes && results.vocabularyNotes.length > 0 ? `
                <div style="margin-top:var(--space-xl);text-align:left;">
                    <h4 style="font-size:var(--text-small);color:var(--ink-light);margin-bottom:8px;">词汇回顾</h4>
                    ${results.vocabularyNotes.map(vn => `
                        <div style="font-size:var(--text-small);padding:4px 0;color:var(--ink-light);">
                            <strong>${vn.word}</strong> — ${vn.meaning}
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        `;

        document.getElementById('btn-continue').onclick = () => {
            this._checkUnlocks();
            this._renderHomeScreen();
            this._updateStepIndicator();
            this._updateNav();
            this._showScreen('home-screen');
        };

        this._updateStepIndicator();
    },

    /**
     * 显示练习结果
     */
    _showResults() {
        const total = this.correctCount + this.wrongCount;
        const score = total > 0 ? Math.round((this.correctCount / total) * 100) : 0;
        const xpEarned = this.correctCount * 10 + (this.correctCount === total ? 20 : 0);

        const userData = Storage.getUserData();
        userData.totalXp = (userData.totalXp || 0) + xpEarned;
        Storage.setUserData(userData);

        // 更新解锁状态
        this._checkUnlocks();

        this._showScreen('results-screen');

        // 获取当前步骤的掌握统计
        let stepStats = '';
        if (this.currentStep === 1) {
            const opsScore = OperationsEngine.getScore();
            stepStats = `操作词掌握：${opsScore.mastered}/${opsScore.total}`;
        } else if (this.currentStep === 2) {
            const thingsScore = VocabularyEngine.getScore('things');
            stepStats = `事物词掌握：${thingsScore.mastered}/${thingsScore.total}`;
        } else if (this.currentStep === 3) {
            const qualityScore = VocabularyEngine.getScore('qualities');
            stepStats = `属性词掌握：${qualityScore.mastered}/${qualityScore.total}`;
        } else if (this.currentStep === 4) {
            const paraStats = ParaphrasingEngine.getStats();
            stepStats = `转述练习：${paraStats.correct}/${paraStats.total}`;
        }

        document.getElementById('result-mastered').textContent = `${score}%`;
        let wrongReviewHTML = '';
        if (this.wrongAnswers.length > 0) {
            wrongReviewHTML = `
                <div style="margin-top:24px;text-align:left;">
                    <div style="font-size:var(--text-small);color:var(--ink-light);font-weight:600;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;">错题回顾</div>
                    ${this.wrongAnswers.map((wa, i) => `
                        <div style="background:var(--paper-dark);border-radius:12px;padding:16px;margin-bottom:8px;">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                                <span style="font-family:var(--font-display);font-size:20px;font-weight:700;color:var(--ink);">${wa.word}</span>
                                <span style="font-size:var(--text-caption);color:var(--ink-faint);">${wa.chinese}</span>
                            </div>
                            ${wa.displayType === 'combination' ? `
                                <div style="font-size:var(--text-small);color:var(--ink-light);margin-top:4px;">
                                    <span style="text-decoration:line-through;color:var(--error);">${wa.verb} ${wa.userAnswer}</span>
                                    <span style="color:var(--ink-faint);margin:0 4px;">→</span>
                                    <span style="color:var(--success);font-weight:600;">${wa.verb} ${wa.correctAnswer}</span>
                                    ${wa.replaces ? `<span style="color:var(--ink-faint);margin-left:4px;">替代 ${wa.replaces.join(', ')}</span>` : ''}
                                    ${wa.example ? `<div style="font-family:var(--font-display);font-style:italic;font-size:var(--text-small);color:var(--ink);margin-top:4px;">"${wa.example}"</div>` : ''}
                                </div>
                            ` : `
                                <div style="font-size:var(--text-small);color:var(--ink-light);margin-top:4px;">
                                    你的答案: <span style="text-decoration:line-through;color:var(--error);">${wa.userAnswer}</span>
                                    <span style="color:var(--ink-faint);margin:0 4px;">→</span>
                                    正确答案: <span style="color:var(--success);font-weight:600;">${wa.correctAnswer}</span>
                                </div>
                            `}
                        </div>
                    `).join('')}
                </div>
            `;
        }
        document.getElementById('result-message').innerHTML = `
            ${this.correctCount} 对 / ${this.wrongCount} 错<br>
            <span style="font-size:var(--text-small);color:var(--ink-faint);">${stepStats} · +${xpEarned} XP</span>
            ${score >= 80
                ? '<br><span style="color:var(--success);">做得很好，继续保持。</span>'
                : '<br><span style="color:var(--ink-light);">慢慢来，已经比上次进步了。</span>'}
            ${wrongReviewHTML}
        `;

        document.getElementById('btn-continue').onclick = () => {
            this._renderHomeScreen();
            this._updateStepIndicator();
            this._updateNav();
            this._showScreen('home-screen');
        };

        this._updateStepIndicator();
        this.inPractice = false;
    },

    /**
     * 更新步骤指示器
     */
    _updateStepIndicator() {
        const userData = Storage.getUserData();
        const unlocks = userData.stepUnlocks || { step1: true, step2: false, step3: false, step4: false, step5: false };

        for (let i = 1; i <= 5; i++) {
            const dot = document.querySelector(`.step-dot[data-step="${i}"]`);
            const line = document.querySelector(`.step-line[data-line="${i}"]`);
            const label = document.querySelector(`.step-label[data-step="${i}"]`);

            if (!dot) continue;

            // 重置
            dot.classList.remove('completed', 'current', 'locked');
            if (label) label.classList.remove('completed', 'current');

            if (i < this.currentStep && unlocks[`step${i}`]) {
                dot.classList.add('completed');
                if (label) label.classList.add('completed');
            } else if (i === this.currentStep) {
                dot.classList.add('current');
                if (label) label.classList.add('current');
            } else if (!unlocks[`step${i}`]) {
                dot.classList.add('locked');
            }

            if (line) {
                line.classList.toggle('completed', i < this.currentStep && unlocks[`step${i}`] && unlocks[`step${i + 1}`]);
            }
        }
    },

    /**
     * 更新底部导航
     */
    _updateNav() {
        const userData = Storage.getUserData();
        const unlocks = userData.stepUnlocks || { step1: true, step2: false, step3: false, step4: false, step5: false };

        document.querySelectorAll('.nav-step').forEach(btn => {
            const step = parseInt(btn.dataset.step);
            btn.classList.remove('active', 'completed', 'locked');

            if (step === this.currentStep) {
                btn.classList.add('active');
            } else if (step < this.currentStep && unlocks[`step${step}`]) {
                btn.classList.add('completed');
            } else if (!unlocks[`step${step}`]) {
                btn.classList.add('locked');
            }
        });
    },

    /**
     * 切换屏幕
     */
    _showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        const screen = document.getElementById(screenId);
        if (screen) {
            screen.classList.add('active');
        }
    },

    /**
     * Toast 提示
     */
    _trackWrongAnswer(exercise, userAnswer, correctAnswer) {
        this.wrongAnswers.push({
            word: exercise.word,
            chinese: exercise.chinese,
            phonetic: exercise.phonetic,
            displayType: exercise.displayType || exercise.mode,
            question: exercise.question,
            userAnswer: userAnswer,
            correctAnswer: correctAnswer || exercise.correctAnswer,
            hint: exercise.hint,
            replaces: exercise.replaces,
            verb: exercise.verb,
            example: exercise.example
        });
    },

    _showToast(message) {
        const existing = document.querySelector('.achievement-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'achievement-toast';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => toast.remove(), 2500);
    },

    /**
     * 绑定所有事件
     */
    _bindEvents() {
        // 底部导航
        document.querySelectorAll('.nav-step').forEach(btn => {
            btn.addEventListener('click', () => {
                const step = parseInt(btn.dataset.step);
                const userData = Storage.getUserData();
                const unlocks = userData.stepUnlocks || {};

                if (!unlocks[`step${step}`]) {
                    this._showToast('此步骤尚未解锁');
                    return;
                }

                if (this.inPractice && step !== this.currentStep) {
                    this.inPractice = false;
                }
                if (this.readingActive && step !== 5) {
                    this.readingActive = false;
                }

                this._startStep(step);
            });
        });

        // 返回按钮（练习页）
        document.getElementById('btn-practice-back').addEventListener('click', () => {
            this.inPractice = false;
            this.readingActive = false;
            this._showScreen('home-screen');
        });

        // 返回按钮（阅读页）
        document.getElementById('btn-reading-back').addEventListener('click', () => {
            this.readingActive = false;
            this._showScreen('home-screen');
        });
    }
};

// 启动应用
document.addEventListener('DOMContentLoaded', () => {
    APP.init();
});

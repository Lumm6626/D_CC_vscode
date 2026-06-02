/**
 * 步骤1：操作词学习引擎
 * 100 个核心动词/功能词
 * 题型：词义匹配、操作词+小品词组合识别、Basic English 单词辨识
 */

const OperationsEngine = {
    words: [],
    currentExercise: null,
    exerciseIndex: 0,
    totalExercises: 5,

    init(words) {
        this.words = words || [];
    },

    /**
     * 生成一组练习
     * @param {number} count - 题目数量
     * @returns {Array} - 练习数组
     */
    generateExercises(count = 10) {
        this.totalExercises = count;
        const progressMap = Storage.getWordProgress();
        const operations = this.words.filter(w => w.type === 'operation');

        if (operations.length === 0) return [];

        const dailyTasks = SRS.getDailyTasks(operations, progressMap, Math.ceil(count / 2), Math.ceil(count / 2));
        let candidateWords = [...dailyTasks.newWords, ...dailyTasks.reviewWords];

        // 如果不够，随机补充
        if (candidateWords.length < count) {
            const remaining = operations.filter(w => !candidateWords.find(c => c.id === w.id));
            const shuffled = SRS.shuffleArray(remaining);
            candidateWords = [...candidateWords, ...shuffled].slice(0, count);
        } else {
            candidateWords = SRS.shuffleArray(candidateWords).slice(0, count);
        }

        const exercises = [];
        for (const word of candidateWords) {
            const type = this._pickExerciseType(word);
            exercises.push(this._createExercise(word, type));
        }

        return exercises;
    },

    _pickExerciseType(word) {
        // 有搭配的操作词 → 搭配识别题；否则 → 词义匹配
        if (word.combinations && word.combinations.length > 0 && Math.random() > 0.5) {
            return 'combination';
        }
        if (Math.random() > 0.7) {
            return 'identification';
        }
        return 'meaning';
    },

    _createExercise(word, type) {
        const base = {
            id: word.id,
            word: word.word,
            chinese: word.chinese,
            phonetic: word.phonetic,
            type: word.type,
            exerciseType: type,
            isOperation: true
        };

        switch (type) {
            case 'meaning':
                return {
                    ...base,
                    displayType: 'meaning',
                    question: '这个词的中文意思是？',
                    options: SRS.generateMeaningOptions(word, this.words, 4),
                    correctAnswer: word.word
                };

            case 'combination':
                const combo = word.combinations[Math.floor(Math.random() * word.combinations.length)];
                const wrongCombos = this._generateWrongCombos(word, combo, 3);
                const comboOptions = SRS.shuffleArray([
                    { verb: word.word, particle: combo.particles, replaces: combo.replaces, correct: true, example: combo.example },
                    ...wrongCombos
                ]);
                return {
                    ...base,
                    displayType: 'combination',
                    verb: word.word,
                    targetParticle: combo.particles,
                    replaces: combo.replaces,
                    example: combo.example,
                    comboOptions: comboOptions,
                    correctParticle: combo.particles
                };

            case 'identification':
                // "哪些词属于 Basic English 的 850 词？"
                const nonBasicWords = [
                    { word: 'physician', isBasic: false },
                    { word: 'automobile', isBasic: false },
                    { word: 'purchase', isBasic: false },
                    { word: 'examine', isBasic: false },
                    { word: 'depart', isBasic: false },
                    { word: 'arrive', isBasic: false },
                    { word: 'attempt', isBasic: false },
                    { word: 'require', isBasic: false },
                    { word: 'demonstrate', isBasic: false },
                    { word: 'frequently', isBasic: false }
                ];
                const idOptions = SRS.generateIdentificationOptions(word, this.words, nonBasicWords, 4);
                return {
                    ...base,
                    displayType: 'identification',
                    question: '哪些是 Basic English 单词？（可多选，点击确认后检查）',
                    idOptions: idOptions
                };

            default:
                return {
                    ...base,
                    displayType: 'meaning',
                    question: '这个词的中文意思是？',
                    options: SRS.generateMeaningOptions(word, this.words, 4),
                    correctAnswer: word.word
                };
        }
    },

    _generateWrongCombos(word, correctCombo, count) {
        const allParticles = ['up', 'down', 'in', 'out', 'on', 'off', 'over', 'through', 'across', 'at', 'by', 'to', 'from', 'with', 'about', 'after', 'before', 'under'];
        const wrongParticles = allParticles.filter(p => p !== correctCombo.particles && (!word.combinations || !word.combinations.find(c => c.particles === p)));
        const shuffled = SRS.shuffleArray(wrongParticles).slice(0, count);

        return shuffled.map(p => ({
            verb: word.word,
            particle: p,
            replaces: ['?'],
            correct: false,
            example: ''
        }));
    },

    checkAnswer(exercise, answer) {
        let correct = false;
        let feedback = '';
        let correctAnswer = '';

        switch (exercise.displayType) {
            case 'meaning':
                correct = answer === exercise.correctAnswer;
                correctAnswer = exercise.correctAnswer;
                feedback = correct ? '正确！' : `正确答案是 "${correctAnswer}"`;
                break;

            case 'combination':
                correct = answer && answer.correct === true;
                correctAnswer = exercise.comboOptions.find(o => o.correct);
                const correctParticle = correctAnswer ? correctAnswer.particle : exercise.correctParticle;
                feedback = correct
                    ? `正确！"${exercise.word} ${correctParticle}" 可以替代 "${exercise.replaces.join(', ')}"`
                    : `正确答案是 "${exercise.word} ${correctParticle}"`;
                break;

            case 'identification':
                // answer is array of selected indices
                const correctIndices = exercise.idOptions
                    .map((o, i) => o.isBasic ? i : -1)
                    .filter(i => i >= 0);
                const selected = answer || [];
                const allCorrect = correctIndices.every(i => selected.includes(i)) &&
                    selected.every(i => correctIndices.includes(i));
                correct = allCorrect;
                correctAnswer = exercise.idOptions
                    .filter(o => o.isBasic)
                    .map(o => o.word)
                    .join(', ');
                feedback = correct
                    ? '完全正确！这些都是 Basic English 单词。'
                    : `Basic English 词是: ${correctAnswer}`;
                break;
        }

        // 更新 SRS 进度
        const progress = Storage.getWordProgressById(exercise.id);
        const currentStrength = progress ? progress.strength : 0;
        const currentStreak = progress ? (progress.correctStreak || 0) : 0;
        const newStreak = correct ? currentStreak + 1 : 0;
        const newStrength = SRS.calculateStrength(currentStrength, correct, currentStreak);
        const nextReview = SRS.calculateNextReview(newStrength, correct, true); // operations: 0.7x interval

        Storage.updateWordProgress(exercise.id, {
            strength: newStrength,
            correctStreak: newStreak,
            nextReview: nextReview,
            timesCorrect: (progress ? progress.timesCorrect : 0) + (correct ? 1 : 0),
            timesWrong: (progress ? progress.timesWrong : 0) + (correct ? 0 : 1),
            lastSeen: new Date().toISOString()
        });

        return {
            correct,
            feedback,
            correctAnswer: typeof correctAnswer === 'string' ? correctAnswer : (correctAnswer.text || correctAnswer)
        };
    },

    getScore() {
        const progressMap = Storage.getWordProgress();
        const operations = this.words.filter(w => w.type === 'operation');
        const total = operations.length;
        const mastered = operations.filter(w => {
            const p = progressMap[w.id];
            return p && p.strength >= 4;
        }).length;
        return { total, mastered, percent: total > 0 ? Math.round((mastered / total) * 100) : 0 };
    }
};

window.OperationsEngine = OperationsEngine;

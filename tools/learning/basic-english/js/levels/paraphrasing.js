/**
 * 步骤4：转述练习引擎
 * 核心差异化功能：将复杂英语改写为 Basic English
 * 题型：选择题、非 Basic 词识别、自由输入 + 实时验证
 */

const ParaphrasingEngine = {
    examples: [],
    words: [],
    currentExercise: null,
    currentMode: 'choice', // 'choice' | 'identify' | 'free_input'

    init(examples, words) {
        this.examples = examples || [];
        this.words = words || [];
    },

    /**
     * 生成一组转述练习
     * @param {number} count
     * @returns {Array}
     */
    generateExercises(count = 10) {
        if (this.examples.length === 0) return [];

        const shuffled = SRS.shuffleArray([...this.examples]);
        const selected = shuffled.slice(0, count);

        const exercises = [];
        for (let i = 0; i < selected.length; i++) {
            const mode = this._pickMode(i);
            exercises.push(this._createExercise(selected[i], mode));
        }

        return exercises;
    },

    _pickMode(index) {
        // 交替题型：选择题、识别题、自由输入
        const modes = ['choice', 'identify', 'free_input', 'choice', 'identify'];
        return modes[index % modes.length];
    },

    _createExercise(example, mode) {
        const base = {
            id: example.id,
            normal: example.normal,
            basic: example.basic,
            difficulty: example.difficulty,
            topic: example.topic,
            hint: example.hint,
            keywords_replaced: example.keywords_replaced,
            mode: mode
        };

        switch (mode) {
            case 'choice':
                return {
                    ...base,
                    question: `将以下句子改写为 Basic English：`,
                    options: this._generateChoiceOptions(example)
                };

            case 'identify':
                return {
                    ...base,
                    question: `以下句子中，哪些词不在 Basic English 850 词中？`,
                    sentence: example.normal,
                    nonBasicIndices: this._findNonBasicIndices(example.normal)
                };

            case 'free_input':
                return {
                    ...base,
                    question: `请将以下句子改写为 Basic English（只用 850 个基础词）：`,
                    inputMode: true
                };

            default:
                return {
                    ...base,
                    question: `将以下句子改写为 Basic English：`,
                    options: this._generateChoiceOptions(example)
                };
        }
    },

    _generateChoiceOptions(example) {
        const options = [
            { text: example.basic, correct: true }
        ];

        // 从其他 examples 中取干扰项
        const others = this.examples.filter(e => e.id !== example.id);
        const shuffled = SRS.shuffleArray(others);

        for (let i = 0; i < shuffled.length && options.length < 4; i++) {
            const wrong = shuffled[i].basic;
            if (!options.find(o => o.text === wrong)) {
                options.push({ text: wrong, correct: false });
            }
        }

        return SRS.shuffleArray(options);
    },

    _findNonBasicIndices(sentence) {
        if (!BasicChecker.basicWordSet) return [];
        const tokens = BasicChecker.tokenize(sentence);
        const indices = [];
        for (const token of tokens) {
            if (!BasicChecker.isBasicWord(token.raw)) {
                indices.push({ word: token.raw, index: token.index });
            }
        }
        return indices;
    },

    checkAnswer(exercise, answer) {
        let correct = false;
        let feedback = '';
        let result = {};

        switch (exercise.mode) {
            case 'choice':
                correct = answer && answer.correct === true;
                feedback = correct
                    ? '正确！这就是标准的 Basic English 表达。'
                    : `更好的改写是："${exercise.basic}"`;
                result.correctAnswer = exercise.basic;
                result.hint = exercise.hint;
                break;

            case 'identify':
                // answer is array of words the user identified as non-Basic
                const actualNonBasic = this._findNonBasicIndices(exercise.normal);
                const actualWords = actualNonBasic.map(nb => nb.word.toLowerCase());
                const userWords = (answer || []).map(w => w.toLowerCase());

                const allFound = actualWords.every(w => userWords.includes(w));
                const noExtra = userWords.every(w => actualWords.includes(w));
                correct = allFound && noExtra;

                if (correct) {
                    feedback = '完全正确！你准确地找出了所有非 Basic English 词汇。';
                } else {
                    const missed = actualWords.filter(w => !userWords.includes(w));
                    const extra = userWords.filter(w => !actualWords.includes(w));
                    feedback = '';
                    if (missed.length > 0) {
                        feedback += `遗漏：${missed.join(', ')}。`;
                    }
                    if (extra.length > 0) {
                        feedback += `${extra.join(', ')} 是 Basic English 词。`;
                    }
                }
                result.correctAnswer = actualWords.join(', ');
                result.hint = exercise.hint;
                break;

            case 'free_input':
                // 使用 BasicChecker 验证用户输入
                const checkResult = BasicChecker.checkSentence(answer || '');
                const scoreThreshold = exercise.difficulty === 'hard' ? 80 : 90;
                correct = checkResult.score >= scoreThreshold;
                feedback = correct
                    ? `很好！你的改写达到了 ${checkResult.score}% Basic English 纯度。`
                    : `你的改写中有 ${checkResult.invalidWords.length} 个非 Basic English 词：${checkResult.invalidWords.map(w => w.word).join(', ')}。目标纯度：${scoreThreshold}%`;

                result.checkerResult = checkResult;
                result.suggestions = checkResult.suggestions;
                result.correctAnswer = exercise.basic;
                result.hint = exercise.hint;
                break;
        }

        // 记录转述历史
        Storage.addParaphrasingEntry({
            exerciseId: exercise.id,
            mode: exercise.mode,
            normal: exercise.normal,
            basic: exercise.basic,
            userAnswer: typeof answer === 'string' ? answer : JSON.stringify(answer),
            correct: correct
        });

        return {
            correct,
            feedback,
            ...result
        };
    },

    getStats() {
        const history = Storage.getParaphrasingHistory();
        const total = history.length;
        const correct = history.filter(h => h.correct).length;
        return {
            total,
            correct,
            percent: total > 0 ? Math.round((correct / total) * 100) : 0
        };
    },

    /**
     * 获取纯自由输入练习（不在 exercise 列表中的，即时生成）
     */
    getFreeInputExercise() {
        const available = this.examples.filter(e => e.difficulty !== 'hard');
        if (available.length === 0) return null;

        const example = available[Math.floor(Math.random() * available.length)];
        return {
            id: example.id + '_free',
            normal: example.normal,
            basic: example.basic,
            difficulty: example.difficulty,
            topic: example.topic,
            hint: example.hint,
            keywords_replaced: example.keywords_replaced,
            mode: 'free_input',
            question: '请将以下句子改写为 Basic English（只用 850 个基础词）：',
            inputMode: true
        };
    }
};

window.ParaphrasingEngine = ParaphrasingEngine;

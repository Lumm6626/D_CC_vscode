/**
 * 高级练习逻辑
 * 级别: Advanced (Level 3)
 * 目标用户: 词汇量 6000+，目标雅思7分+
 */

const AdvancedLevel = {
    name: 'advanced',
    displayName: '高级',

    /**
     * 生成练习题目
     * @param {Array} words - 单词列表
     * @param {number} count - 题目数量
     * @returns {Array}
     */
    generateExercises(words, count = 5) {
        const exercises = [];
        const shuffledWords = this.shuffleArray([...words]).slice(0, count);

        for (const word of shuffledWords) {
            const exerciseType = this.getRandomExerciseType();
            exercises.push(this.createExercise(word, exerciseType));
        }

        return exercises;
    },

    /**
     * 获取练习类型
     */
    getExerciseTypes() {
        return [
            { type: 'synonym选择题', weight: 30, description: '同义词匹配' },
            { type: 'context阅读', weight: 25, description: '阅读理解' },
            { type: 'timer抢答', weight: 25, description: '计时挑战' },
            { type: 'fill填空', weight: 20, description: '句子翻译' }
        ];
    },

    /**
     * 获取随机练习类型
     */
    getRandomExerciseType() {
        const types = this.getExerciseTypes();
        const random = Math.random() * 100;
        let cumulative = 0;

        for (const t of types) {
            cumulative += t.weight;
            if (random <= cumulative) {
                return t.type;
            }
        }

        return types[0].type;
    },

    /**
     * 创建练习题目
     */
    createExercise(word, type) {
        const base = {
            id: word.id,
            word: word.word,
            meaning: word.meaning,
            level: 3,
            type: type
        };

        switch (type) {
            case 'synonym选择题':
                return this.createSynonymQuestion(word, base);
            case 'context阅读':
                return this.createContextQuestion(word, base);
            case 'timer抢答':
                return this.createTimerQuestion(word, base);
            case 'fill填空':
                return this.createTranslateQuestion(word, base);
            default:
                return this.createSynonymQuestion(word, base);
        }
    },

    /**
     * 创建同义词匹配题目
     */
    createSynonymQuestion(word, base) {
        const synonyms = word.synonyms || this.generateSynonyms(word);

        return {
            ...base,
            question: `请选择与"${word.word}"意思最相近的单词`,
            options: this.generateSynonymOptions(word, synonyms, 4),
            correctAnswer: word.word
        };
    },

    /**
     * 创建阅读理解题目
     */
    createContextQuestion(word, base) {
        const context = word.context || this.generateContext(word);

        return {
            ...base,
            context: context,
            question: `在上面的文章中，"${word.word}"是什么意思？`,
            options: this.generateMeaningOptions(word, 4),
            correctAnswer: word.meaning
        };
    },

    /**
     * 创建计时抢答题目
     */
    createTimerQuestion(word, base) {
        return {
            ...base,
            timeLimit: 10, // 10秒
            question: `快速选择"${word.word}"的含义！`,
            options: this.generateMeaningOptions(word, 4),
            correctAnswer: word.meaning
        };
    },

    /**
     * 创建句子翻译题目
     */
    createTranslateQuestion(word, base) {
        const sentence = word.sentence || this.generateSentence(word);

        return {
            ...base,
            sentence: sentence,
            question: `请将这个句子翻译成英文（使用"${word.word}"）`,
            hint: `使用单词: ${word.word}`,
            correctAnswer: word.word
        };
    },

    /**
     * 生成同义词
     */
    generateSynonyms(word) {
        // 常见的同义词映射
        const synonymMap = {
            'abandon': ['leave', 'desert', 'quit', 'forsake'],
            'establish': ['found', 'set up', 'create', 'build'],
            'emphasize': ['stress', 'highlight', 'underline', 'stress'],
            'indicate': ['show', 'suggest', 'imply', 'demonstrate'],
            'approach': ['method', 'way', 'manner', 'technique'],
            'benefit': ['help', 'aid', 'assist', 'profit'],
            'calculate': ['compute', 'estimate', 'determine', 'reckon'],
            'confirm': ['verify', 'prove', 'validate', 'establish'],
            'demonstrate': ['show', 'illustrate', 'exhibit', 'display'],
            'estimate': ['assess', 'evaluate', 'appraise', 'judge']
        };

        return synonymMap[word.word.toLowerCase()] || [];
    },

    /**
     * 生成同义词选项
     */
    generateSynonymOptions(word, synonyms, count) {
        const options = [word.word];

        // 添加同义词
        for (const syn of synonyms) {
            if (options.length >= count) break;
            if (!options.includes(syn)) {
                options.push(syn);
            }
        }

        // 补充干扰项
        while (options.length < count) {
            const fakeWord = this.generateFakeWord();
            if (!options.includes(fakeWord)) {
                options.push(fakeWord);
            }
        }

        return this.shuffleArray(options);
    },

    /**
     * 生成中文含义选项
     */
    generateMeaningOptions(targetWord, count) {
        const options = [targetWord.meaning];

        const commonMeanings = [
            '执行，实施', '研究，调查', '发展，发育', '影响，作用',
            '创建，建立', '提供，给予', '接受，承认', '拒绝，否认',
            '帮助，援助', '支持，赞成', '反对，抵抗', '增加，增长',
            '减少，下降', '改变，转变', '保持，保留', '结束，终止',
            '开始，启动', '继续，持续', '完成，实现', '成功，完成',
            '分析，研究', '评估，评价', '证明，证实', '表明，显示',
            '建议，提倡', '表明，主张', '证实，论证', '归纳，总结',
            '证明，表明', '推测，假设', '证实，验证', '概括，总结',
            '阐述，说明', '阐述，解释', '表明，指出', '建议，暗示'
        ];

        const filteredMeanings = commonMeanings.filter(m => m !== targetWord.meaning);
        const shuffledMeanings = this.shuffleArray(filteredMeanings);

        for (const meaning of shuffledMeanings) {
            if (options.length >= count) break;
            if (!options.includes(meaning)) {
                options.push(meaning);
            }
        }

        return this.shuffleArray(options);
    },

    /**
     * 生成语境
     */
    generateContext(word) {
        const templates = [
            `The ${word.word} of new technologies has dramatically changed how we work. In particular, the ${word.word} of digital tools in education has been remarkable.`,
            `Researchers continue to ${word.word} the relationship between climate change and human activity. The evidence suggests that we must ${word.word} our approach to environmental protection.`,
            `The study aims to ${word.word} the key factors that contribute to economic growth. Through careful analysis, we can ${word.word} the true impact of various policies.`,
            `To ${word.word} this complex issue, we need to consider multiple perspectives. The ${word.word} of interdisciplinary research has become increasingly important.`,
            `The committee decided to ${word.word} the proposal after careful consideration. This ${word.word} reflects the need for more comprehensive planning.`
        ];

        return templates[Math.floor(Math.random() * templates.length)];
    },

    /**
     * 生成句子
     */
    generateSentence(word) {
        const templates = [
            `It is essential to ${word.word} the findings of this research.`,
            `The government plans to ${word.word} new regulations next month.`,
            `We need to ${word.word} our strategy in light of recent developments.`,
            `The company aims to ${word.word} its market position through innovation.`,
            `Researchers will ${word.word} the experiment under controlled conditions.`
        ];

        return templates[Math.floor(Math.random() * templates.length)];
    },

    /**
     * 生成假单词
     */
    generateFakeWord() {
        const prefixes = ['ab', 'de', 'in', 'ex', 'pre', 're', 'pro', 'un', 'dis', 'mis'];
        const roots = ['late', 'form', 'port', 'ject', 'duct', 'scribe', 'struct', 'mit', 'tend', 'vert'];
        const suffixes = ['ion', 'ment', 'ness', 'ty', 'ure', 'ance', 'ence', 'able', 'ible', 'al'];

        const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
        const root = roots[Math.floor(Math.random() * roots.length)];
        const suffix = suffixes[Math.floor(Math.random() * suffixes.length)];

        return prefix + root + suffix;
    },

    /**
     * 打乱数组
     */
    shuffleArray(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    },

    /**
     * 处理答案
     */
    checkAnswer(exercise, answer) {
        // 计时题和翻译题忽略大小写
        if (exercise.type === 'timer抢答' || exercise.type === 'fill填空') {
            const correct = answer.toLowerCase().trim() === exercise.correctAnswer.toLowerCase().trim();
            return {
                correct,
                feedback: correct ? '正确！' : `正确答案是: ${exercise.correctAnswer}`,
                correctAnswer: exercise.correctAnswer
            };
        }

        // 选择题精确匹配
        const correct = answer === exercise.correctAnswer ||
                       answer === exercise.options.find(o => o === exercise.correctAnswer);

        return {
            correct,
            feedback: correct ? '正确！' : `正确答案是: ${exercise.correctAnswer}`,
            correctAnswer: exercise.correctAnswer
        };
    },

    /**
     * 计算奖励
     */
    calculateReward(correct, streak, timeRemaining = null) {
        let xp = 0;

        if (correct) {
            xp = 15; // 高级比进阶再多3xp

            // 计时题额外奖励
            if (exercise.type === 'timer抢答' && timeRemaining !== null) {
                const timeBonus = Math.floor(timeRemaining / 2);
                xp += timeBonus;
            }

            if (streak > 0 && streak % 5 === 0) {
                xp += 5;
            }
        }

        return { xp, hearts: correct ? 0 : -1 };
    },

    /**
     * 获取练习描述
     */
    getExerciseDescription(type) {
        const descriptions = {
            'synonym选择题': '选择与目标单词意思最相近的选项',
            'context阅读': '根据文章上下文理解单词含义',
            'timer抢答': '在限定时间内快速选择正确答案',
            'fill填空': '将句子翻译成英文'
        };
        return descriptions[type] || '选择正确答案';
    }
};

// 导出
window.AdvancedLevel = AdvancedLevel;
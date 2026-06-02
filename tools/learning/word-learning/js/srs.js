/**
 * 间隔重复算法 (Spaced Repetition System)
 * 基于 SM-2 算法简化版
 */

const SRS = {
    // 间隔天数配置（天）
    intervals: [1, 2, 4, 7, 15, 30],

    // 强度等级配置
    strengthThresholds: {
        0: 0,    // 新单词
        1: 1,    // 学习中
        2: 3,    // 较熟悉
        3: 5,    // 熟悉
        4: 7,    // 掌握
        5: 10    // 精通
    },

    /**
     * 计算下次复习日期
     * @param {number} strength - 当前记忆强度
     * @param {boolean} correct - 本次是否正确
     * @returns {string} - ISO格式的日期字符串
     */
    calculateNextReview(strength, correct) {
        if (!correct) {
            // 错误时，缩短间隔，回到较短间隔
            strength = Math.max(0, strength - 1);
        }

        const intervalIndex = Math.min(strength, this.intervals.length - 1);
        const intervalDays = this.intervals[intervalIndex];

        const nextDate = new Date();
        nextDate.setDate(nextDate.getDate() + intervalDays);

        return nextDate.toISOString();
    },

    /**
     * 计算记忆强度
     * @param {number} currentStrength - 当前强度
     * @param {boolean} correct - 是否正确
     * @param {number} correctStreak - 连续正确次数
     * @returns {number} - 新强度
     */
    calculateStrength(currentStrength, correct, correctStreak) {
        if (correct) {
            // 连续正确会增加强度
            const streakBonus = Math.min(Math.floor(correctStreak / 3), 2);
            return Math.min(5, currentStrength + 1 + streakBonus);
        } else {
            // 错误会降低强度
            return Math.max(0, currentStrength - 1);
        }
    },

    /**
     * 检查单词是否需要复习
     * @param {Object} wordProgress - 单词进度对象
     * @returns {boolean}
     */
    needsReview(wordProgress) {
        if (!wordProgress || !wordProgress.nextReview) return true;

        const now = new Date();
        const nextReview = new Date(wordProgress.nextReview);

        return now >= nextReview;
    },

    /**
     * 获取需要复习的单词列表
     * @param {Array} words - 单词列表
     * @param {Object} progressMap - 进度映射
     * @param {number} limit - 限制数量
     * @returns {Array} - 需要复习的单词
     */
    getReviewQueue(words, progressMap, limit = 10) {
        const now = new Date();
        const reviewQueue = [];

        for (const word of words) {
            const progress = progressMap[word.id];
            if (!progress) {
                // 新单词需要学习
                reviewQueue.push({ word, priority: 100 });
            } else if (progress.nextReview) {
                const nextReview = new Date(progress.nextReview);
                if (now >= nextReview) {
                    // 需要复习
                    const overdueDays = Math.floor((now - nextReview) / (1000 * 60 * 60 * 24));
                    reviewQueue.push({ word, priority: overdueDays + progress.strength });
                }
            }
        }

        // 按优先级排序
        reviewQueue.sort((a, b) => b.priority - a.priority);

        return reviewQueue.slice(0, limit).map(item => item.word);
    },

    /**
     * 获取每日学习任务
     * @param {Array} words - 单词列表
     * @param {Object} progressMap - 进度映射
     * @param {number} newWordsCount - 新单词数量
     * @param {number} reviewCount - 复习单词数量
     * @returns {Object} - { newWords, reviewWords }
     */
    getDailyTasks(words, progressMap, newWordsCount = 3, reviewCount = 7) {
        const now = new Date();
        const newWords = [];
        const reviewWords = [];

        // 收集需要复习的单词
        const reviewQueue = [];
        for (const word of words) {
            const progress = progressMap[word.id];
            if (!progress) {
                newWords.push(word);
            } else if (progress.nextReview && now >= new Date(progress.nextReview)) {
                reviewQueue.push(word);
            }
        }

        // 限制新单词数量
        const selectedNewWords = newWords.slice(0, newWordsCount);
        const selectedReviewWords = reviewQueue.slice(0, reviewCount);

        return {
            newWords: selectedNewWords,
            reviewWords: selectedReviewWords
        };
    },

    /**
     * 生成练习题目
     * @param {Array} words - 单词列表
     * @param {Object} progressMap - 进度映射
     * @param {number} count - 题目数量
     * @returns {Array} - 练习题目
     */
    generateExercises(words, progressMap, count = 5) {
        const tasks = this.getDailyTasks(words, progressMap, count, count);
        const exercises = [];

        // 混合新单词和复习单词
        const allWords = [...tasks.newWords, ...tasks.reviewWords];

        for (const word of allWords.slice(0, count)) {
            const progress = progressMap[word.id];
            const exerciseType = this.getExerciseType(word.level || 1, progress);
            exercises.push(this.createExercise(word, exerciseType));
        }

        return exercises;
    },

    /**
     * 根据级别和进度获取练习类型
     * @param {number} level - 级别
     * @param {Object} progress - 进度
     * @returns {string} - 练习类型
     */
    getExerciseType(level, progress) {
        const types = {
            1: ['image选择题', 'listen选择题', 'word选择题'],
            2: ['fill填空', 'listen拼写', 'match配对'],
            3: ['synonym选择题', 'context阅读', 'timer抢答']
        };

        const levelTypes = types[level] || types[1];
        return levelTypes[Math.floor(Math.random() * levelTypes.length)];
    },

    /**
     * 创建练习题目
     * @param {Object} word - 单词对象
     * @param {string} type - 练习类型
     * @returns {Object} - 练习题目
     */
    createExercise(word, type) {
        const base = {
            id: word.id,
            word: word.word,
            meaning: word.meaning,
            level: word.level || 1,
            type: type
        };

        switch (type) {
            case 'image选择题':
                return {
                    ...base,
                    image: word.image || null,
                    options: this.generateOptions(word, 4),
                    correctAnswer: word.word
                };
            case 'listen选择题':
            case 'word选择题':
                return {
                    ...base,
                    audio: word.audio || word.word,
                    options: this.generateOptions(word, 4),
                    correctAnswer: word.word
                };
            case 'fill填空':
                return {
                    ...base,
                    sentence: word.example || `The word "${word.word}" means: ${word.meaning}`,
                    hint: word.word[0] + '_'.repeat(word.word.length - 1),
                    correctAnswer: word.word
                };
            case 'listen拼写':
                return {
                    ...base,
                    audio: word.audio || word.word,
                    correctAnswer: word.word
                };
            case 'match配对':
                return {
                    ...base,
                    pairs: this.generatePairs(word),
                    correctAnswer: word.word
                };
            case 'synonym选择题':
                return {
                    ...base,
                    synonyms: word.synonyms || [],
                    options: this.generateSynonymOptions(word, 4),
                    correctAnswer: word.word
                };
            case 'context阅读':
                return {
                    ...base,
                    context: word.context || word.example || `The word "${word.word}" is used in academic contexts.`,
                    correctAnswer: word.word
                };
            case 'timer抢答':
                return {
                    ...base,
                    timeLimit: 10,
                    options: this.generateOptions(word, 4),
                    correctAnswer: word.word
                };
            default:
                return {
                    ...base,
                    options: this.generateOptions(word, 4),
                    correctAnswer: word.word
                };
        }
    },

    /**
     * 生成选项
     * @param {Object} word - 目标单词
     * @param {number} count - 选项数量
     * @returns {Array} - 选项数组
     */
    generateOptions(word, count = 4) {
        // 简单实现：使用相近的中文释义作为干扰项
        const options = [word.meaning];
        const meanings = [
            '执行，实施', '研究，调查', '发展，发育', '影响，作用',
            '创建，建立', '提供，给予', '接受，承认', '拒绝，否认',
            '帮助，援助', '支持，赞成', '反对，抵抗', '增加，增长',
            '减少，下降', '改变，转变', '保持，保留', '结束，终止',
            '开始，启动', '继续，持续', '完成，实现', '成功，完成'
        ];

        while (options.length < count) {
            const randomMeaning = meanings[Math.floor(Math.random() * meanings.length)];
            if (!options.includes(randomMeaning)) {
                options.push(randomMeaning);
            }
        }

        // 打乱顺序
        return this.shuffleArray(options);
    },

    /**
     * 生成同义词选项
     * @param {Object} word - 目标单词
     * @param {number} count - 选项数量
     * @returns {Array}
     */
    generateSynonymOptions(word, count = 4) {
        const synonyms = word.synonyms || ['同义词1', '同义词2'];
        return this.shuffleArray([word.word, ...synonyms.slice(0, count - 1)]);
    },

    /**
     * 生成配对
     * @param {Object} word - 单词对象
     * @returns {Array}
     */
    generatePairs(word) {
        return [
            { left: word.word, right: word.meaning }
        ];
    },

    /**
     * 打乱数组
     * @param {Array} array - 输入数组
     * @returns {Array} - 打乱后的数组
     */
    shuffleArray(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }
};

// 导出
window.SRS = SRS;
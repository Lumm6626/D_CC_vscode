/**
 * 间隔重复算法 (Spaced Repetition System)
 * 基于 SM-2 算法简化版，针对 Basic English 操作词增加 0.7x 复习间隔
 */

const SRS = {
    intervals: [1, 2, 4, 7, 15, 30],

    strengthThresholds: {
        0: 0,
        1: 1,
        2: 3,
        3: 5,
        4: 7,
        5: 10
    },

    /**
     * 计算下次复习日期
     * @param {number} strength - 当前记忆强度
     * @param {boolean} correct - 本次是否正确
     * @param {boolean} isOperation - 是否为操作词（操作词间隔缩短为 0.7x）
     * @returns {string} - ISO格式的日期字符串
     */
    calculateNextReview(strength, correct, isOperation = false) {
        if (!correct) {
            strength = Math.max(0, strength - 1);
        }

        const intervalIndex = Math.min(strength, this.intervals.length - 1);
        let intervalDays = this.intervals[intervalIndex];

        if (isOperation) {
            intervalDays = Math.max(1, Math.round(intervalDays * 0.7));
        }

        const nextDate = new Date();
        nextDate.setDate(nextDate.getDate() + intervalDays);

        return nextDate.toISOString();
    },

    calculateStrength(currentStrength, correct, correctStreak) {
        if (correct) {
            const streakBonus = Math.min(Math.floor(correctStreak / 3), 2);
            return Math.min(5, currentStrength + 1 + streakBonus);
        } else {
            return Math.max(0, currentStrength - 1);
        }
    },

    needsReview(wordProgress) {
        if (!wordProgress || !wordProgress.nextReview) return true;

        const now = new Date();
        const nextReview = new Date(wordProgress.nextReview);

        return now >= nextReview;
    },

    getReviewQueue(words, progressMap, limit = 10) {
        const now = new Date();
        const reviewQueue = [];

        for (const word of words) {
            const progress = progressMap[word.id];
            if (!progress) {
                reviewQueue.push({ word, priority: 100 });
            } else if (progress.nextReview) {
                const nextReview = new Date(progress.nextReview);
                if (now >= nextReview) {
                    const overdueDays = Math.floor((now - nextReview) / (1000 * 60 * 60 * 24));
                    reviewQueue.push({ word, priority: overdueDays + progress.strength });
                }
            }
        }

        reviewQueue.sort((a, b) => b.priority - a.priority);

        return reviewQueue.slice(0, limit).map(item => item.word);
    },

    getDailyTasks(words, progressMap, newWordsCount = 3, reviewCount = 7) {
        const now = new Date();
        const newWords = [];
        const reviewWords = [];

        for (const word of words) {
            const progress = progressMap[word.id];
            if (!progress) {
                newWords.push(word);
            } else if (progress.nextReview && now >= new Date(progress.nextReview)) {
                reviewWords.push(word);
            }
        }

        const selectedNewWords = newWords.slice(0, newWordsCount);
        const selectedReviewWords = reviewWords.slice(0, reviewCount);

        return {
            newWords: selectedNewWords,
            reviewWords: selectedReviewWords
        };
    },

    shuffleArray(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    },

    /**
     * 为 Basic English 词义匹配练习生成选项
     * @param {Object} targetWord - 目标词
     * @param {Array} allWords - 所有词（用于生成干扰项）
     * @param {number} count - 选项数量
     * @returns {Array} - 选项数组 [{word, chinese}]
     */
    generateMeaningOptions(targetWord, allWords, count = 4) {
        const options = [{ word: targetWord.word, chinese: targetWord.chinese }];
        const otherWords = allWords.filter(w => w.id !== targetWord.id);

        const shuffled = this.shuffleArray(otherWords);

        for (let i = 0; i < shuffled.length && options.length < count; i++) {
            const w = shuffled[i];
            if (!options.find(o => o.chinese === w.chinese)) {
                options.push({ word: w.word, chinese: w.chinese });
            }
        }

        return this.shuffleArray(options);
    },

    /**
     * 生成 Basic English 单词辨识题选项（哪些是 Basic English 词）
     */
    generateIdentificationOptions(targetWord, allBasicWords, nonBasicWords, count = 4) {
        const options = [{ word: targetWord.word, isBasic: true }];
        const basicPool = allBasicWords.filter(w => w.id !== targetWord.id);
        const otherBasic = this.shuffleArray(basicPool).slice(0, Math.floor((count - 1) / 2));
        const otherNonBasic = this.shuffleArray(nonBasicWords).slice(0, Math.ceil((count - 1) / 2));

        for (const w of otherBasic) {
            options.push({ word: w.word, isBasic: true });
        }
        for (const w of otherNonBasic) {
            options.push({ word: w.word, isBasic: false });
        }

        return this.shuffleArray(options.slice(0, count));
    }
};

window.SRS = SRS;

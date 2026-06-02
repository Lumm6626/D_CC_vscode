/**
 * localStorage 封装模块
 */

const Storage = {
    KEYS: {
        USER_DATA: 'toefl_user_data',
        WORD_PROGRESS: 'toefl_word_progress',
        SETTINGS: 'toefl_settings',
        WORD_CACHE: 'toefl_word_cache'
    },

    // 获取默认用户数据
    getDefaultUserData() {
        return {
            currentLevel: 1,
            totalXp: 0,
            hearts: 5,
            streak: 0,
            lastLearnDate: '',
            streakFreezes: 0,
            achievements: [],
            createdAt: new Date().toISOString(),
            wordsLearned: [],
            streakDates: []
        };
    },

    // 获取默认设置
    getDefaultSettings() {
        return {
            ttsSpeed: 1,
            soundEnabled: true,
            reminderEnabled: false,
            reminderTime: '09:00'
        };
    },

    // 获取用户数据
    getUserData() {
        const data = localStorage.getItem(this.KEYS.USER_DATA);
        if (!data) {
            const defaultData = this.getDefaultUserData();
            this.setUserData(defaultData);
            return defaultData;
        }
        return JSON.parse(data);
    },

    // 设置用户数据
    setUserData(data) {
        localStorage.setItem(this.KEYS.USER_DATA, JSON.stringify(data));
    },

    // 更新用户数据（合并）
    updateUserData(updates) {
        const currentData = this.getUserData();
        const newData = { ...currentData, ...updates };
        this.setUserData(newData);
        return newData;
    },

    // 获取单词进度
    getWordProgress() {
        const data = localStorage.getItem(this.KEYS.WORD_PROGRESS);
        return data ? JSON.parse(data) : {};
    },

    // 设置单词进度
    setWordProgress(progress) {
        localStorage.setItem(this.KEYS.WORD_PROGRESS, JSON.stringify(progress));
    },

    // 更新单个单词进度
    updateWordProgress(wordId, updates) {
        const progress = this.getWordProgress();
        if (!progress[wordId]) {
            progress[wordId] = {
                wordId: wordId,
                strength: 0,
                correctStreak: 0,
                nextReview: null,
                timesCorrect: 0,
                timesWrong: 0
            };
        }
        progress[wordId] = { ...progress[wordId], ...updates };
        this.setWordProgress(progress);
        return progress[wordId];
    },

    // 获取单词进度
    getWordProgressById(wordId) {
        const progress = this.getWordProgress();
        return progress[wordId] || null;
    },

    // 获取设置
    getSettings() {
        const data = localStorage.getItem(this.KEYS.SETTINGS);
        if (!data) {
            const defaultSettings = this.getDefaultSettings();
            this.setSettings(defaultSettings);
            return defaultSettings;
        }
        return JSON.parse(data);
    },

    // 设置设置
    setSettings(settings) {
        localStorage.setItem(this.KEYS.SETTINGS, JSON.stringify(settings));
    },

    // 更新设置
    updateSettings(updates) {
        const currentSettings = this.getSettings();
        const newSettings = { ...currentSettings, ...updates };
        this.setSettings(newSettings);
        return newSettings;
    },

    // 获取缓存的单词数据
    getWordCache() {
        const data = localStorage.getItem(this.KEYS.WORD_CACHE);
        return data ? JSON.parse(data) : null;
    },

    // 设置单词缓存
    setWordCache(words) {
        localStorage.setItem(this.KEYS.WORD_CACHE, JSON.stringify(words));
    },

    // 检查是否需要更新每日数据
    checkDailyReset() {
        const userData = this.getUserData();
        const today = new Date().toISOString().split('T')[0];
        const lastLearn = userData.lastLearnDate;

        // 如果是同一天，不需要重置
        if (lastLearn === today) return false;

        // 检查连胜
        if (lastLearn) {
            const lastDate = new Date(lastLearn);
            const todayDate = new Date(today);
            const diffDays = Math.floor((todayDate - lastDate) / (1000 * 60 * 60 * 24));

            if (diffDays > 1) {
                // 连胜中断
                if (userData.streak > 0) {
                    // 检查是否有连胜冻结卡
                    if (userData.streakFreezes > 0) {
                        userData.streakFreezes--;
                        // 保持连胜
                    } else {
                        userData.streak = 0;
                    }
                }
            }
        }

        // 恢复生命值
        if (userData.hearts < 5) {
            userData.hearts = 5;
        }

        userData.lastLearnDate = today;
        this.setUserData(userData);
        return true;
    },

    // 重置所有数据
    resetAll() {
        localStorage.removeItem(this.KEYS.USER_DATA);
        localStorage.removeItem(this.KEYS.WORD_PROGRESS);
        localStorage.removeItem(this.KEYS.SETTINGS);
        // 保留单词缓存
    },

    // 获取学习统计数据
    getStats() {
        const userData = this.getUserData();
        const progress = this.getWordProgress();

        const totalWords = Object.keys(progress).length;
        const masteredWords = Object.values(progress).filter(p => p.strength >= 4).length;
        const learningWords = Object.values(progress).filter(p => p.strength > 0 && p.strength < 4).length;

        return {
            totalXp: userData.totalXp,
            streak: userData.streak,
            hearts: userData.hearts,
            totalWordsLearned: totalWords,
            masteredWords: masteredWords,
            learningWords: learningWords,
            achievements: userData.achievements,
            streakDates: userData.streakDates || []
        };
    }
};

// 导出
window.Storage = Storage;
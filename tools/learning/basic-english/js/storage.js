/**
 * localStorage 封装模块 — Basic English
 * 适配自 word-learning/js/storage.js，换用 be_* 前缀，增加转述历史字段
 */

const Storage = {
    KEYS: {
        USER_DATA: 'be_user_data',
        WORD_PROGRESS: 'be_word_progress',
        SETTINGS: 'be_settings',
        WORD_CACHE: 'be_word_cache',
        PARAPHRASING_HISTORY: 'be_paraphrasing_history',
        READING_HISTORY: 'be_reading_history'
    },

    getDefaultUserData() {
        return {
            currentStep: 1,
            operationsCompleted: 0,
            vocabularyCompleted: 0,
            totalXp: 0,
            streak: 0,
            lastLearnDate: '',
            achievements: [],
            createdAt: new Date().toISOString(),
            stepUnlocks: {
                step1: true,
                step2: false,
                step3: false,
                step4: false,
                step5: false
            }
        };
    },

    getDefaultSettings() {
        return {
            ttsSpeed: 1,
            soundEnabled: true,
            reminderEnabled: false,
            reminderTime: '09:00'
        };
    },

    getUserData() {
        const data = localStorage.getItem(this.KEYS.USER_DATA);
        if (!data) {
            const defaultData = this.getDefaultUserData();
            this.setUserData(defaultData);
            return defaultData;
        }
        return JSON.parse(data);
    },

    setUserData(data) {
        localStorage.setItem(this.KEYS.USER_DATA, JSON.stringify(data));
    },

    updateUserData(updates) {
        const currentData = this.getUserData();
        const newData = { ...currentData, ...updates };
        this.setUserData(newData);
        return newData;
    },

    getWordProgress() {
        const data = localStorage.getItem(this.KEYS.WORD_PROGRESS);
        return data ? JSON.parse(data) : {};
    },

    setWordProgress(progress) {
        localStorage.setItem(this.KEYS.WORD_PROGRESS, JSON.stringify(progress));
    },

    updateWordProgress(wordId, updates) {
        const progress = this.getWordProgress();
        if (!progress[wordId]) {
            progress[wordId] = {
                wordId: wordId,
                strength: 0,
                correctStreak: 0,
                nextReview: null,
                timesCorrect: 0,
                timesWrong: 0,
                lastSeen: null
            };
        }
        progress[wordId] = { ...progress[wordId], ...updates };
        this.setWordProgress(progress);
        return progress[wordId];
    },

    getWordProgressById(wordId) {
        const progress = this.getWordProgress();
        return progress[wordId] || null;
    },

    getSettings() {
        const data = localStorage.getItem(this.KEYS.SETTINGS);
        if (!data) {
            const defaultSettings = this.getDefaultSettings();
            this.setSettings(defaultSettings);
            return defaultSettings;
        }
        return JSON.parse(data);
    },

    setSettings(settings) {
        localStorage.setItem(this.KEYS.SETTINGS, JSON.stringify(settings));
    },

    updateSettings(updates) {
        const currentSettings = this.getSettings();
        const newSettings = { ...currentSettings, ...updates };
        this.setSettings(newSettings);
        return newSettings;
    },

    getWordCache() {
        const data = localStorage.getItem(this.KEYS.WORD_CACHE);
        return data ? JSON.parse(data) : null;
    },

    setWordCache(words) {
        localStorage.setItem(this.KEYS.WORD_CACHE, JSON.stringify(words));
    },

    getParaphrasingHistory() {
        const data = localStorage.getItem(this.KEYS.PARAPHRASING_HISTORY);
        return data ? JSON.parse(data) : [];
    },

    addParaphrasingEntry(entry) {
        const history = this.getParaphrasingHistory();
        history.push({
            ...entry,
            timestamp: new Date().toISOString()
        });
        localStorage.setItem(this.KEYS.PARAPHRASING_HISTORY, JSON.stringify(history));
        return history;
    },

    getReadingHistory() {
        const data = localStorage.getItem(this.KEYS.READING_HISTORY);
        return data ? JSON.parse(data) : [];
    },

    addReadingEntry(entry) {
        const history = this.getReadingHistory();
        history.push({
            ...entry,
            timestamp: new Date().toISOString()
        });
        localStorage.setItem(this.KEYS.READING_HISTORY, JSON.stringify(history));
        return history;
    },

    checkDailyReset() {
        const userData = this.getUserData();
        const today = new Date().toISOString().split('T')[0];
        const lastLearn = userData.lastLearnDate;

        if (lastLearn === today) return false;

        if (lastLearn) {
            const lastDate = new Date(lastLearn);
            const todayDate = new Date(today);
            const diffDays = Math.floor((todayDate - lastDate) / (1000 * 60 * 60 * 24));

            if (diffDays > 1 && userData.streak > 0) {
                userData.streak = 0;
            }
        }

        userData.lastLearnDate = today;

        if (!userData.streak) {
            userData.streak = 0;
        }
        userData.streak++;

        this.setUserData(userData);
        return true;
    },

    resetAll() {
        localStorage.removeItem(this.KEYS.USER_DATA);
        localStorage.removeItem(this.KEYS.WORD_PROGRESS);
        localStorage.removeItem(this.KEYS.SETTINGS);
        localStorage.removeItem(this.KEYS.PARAPHRASING_HISTORY);
        localStorage.removeItem(this.KEYS.READING_HISTORY);
    },

    getStats() {
        const userData = this.getUserData();
        const progress = this.getWordProgress();

        const totalWords = Object.keys(progress).length;
        const masteredWords = Object.values(progress).filter(p => p.strength >= 4).length;
        const learningWords = Object.values(progress).filter(p => p.strength > 0 && p.strength < 4).length;
        const paraphrasingHistory = this.getParaphrasingHistory();
        const readingHistory = this.getReadingHistory();

        return {
            totalXp: userData.totalXp,
            streak: userData.streak,
            currentStep: userData.currentStep,
            totalWordsLearned: totalWords,
            masteredWords: masteredWords,
            learningWords: learningWords,
            achievements: userData.achievements,
            paraphrasingCount: paraphrasingHistory.length,
            readingCount: readingHistory.length,
            stepUnlocks: userData.stepUnlocks
        };
    }
};

window.Storage = Storage;

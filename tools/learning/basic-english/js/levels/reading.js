/**
 * 步骤5：阅读理解引擎
 * Basic English 文章 + 理解问答
 */

const ReadingEngine = {
    passages: [],
    currentPassage: null,
    userAnswers: {},
    questionsAnswered: 0,

    init(passages) {
        this.passages = passages || [];
    },

    getAvailablePassages() {
        return this.passages;
    },

    getPassageById(id) {
        return this.passages.find(p => p.id === id) || null;
    },

    /**
     * 获取推荐的文章（优先未读过的，难度递增）
     * @param {string|null} difficulty - 可选难度过滤
     * @returns {Object|null}
     */
    getRecommendedPassage(difficulty = null) {
        const history = Storage.getReadingHistory();
        const readIds = new Set(history.map(h => h.passageId));

        let pool = this.passages;
        if (difficulty) {
            pool = pool.filter(p => p.difficulty === difficulty);
        }

        // 优先未读
        const unread = pool.filter(p => !readIds.has(p.id));
        if (unread.length > 0) {
            const sorted = unread.sort((a, b) => (a.difficulty === 'easy' ? -1 : 1));
            return sorted[0];
        }

        // 全部读过，返回最久未读的
        if (pool.length > 0) {
            return pool[0];
        }

        return null;
    },

    startPassage(passage) {
        this.currentPassage = passage;
        this.userAnswers = {};
        this.questionsAnswered = 0;
        return {
            id: passage.id,
            title: passage.title,
            text: passage.text,
            source: passage.source,
            word_count: passage.word_count,
            difficulty: passage.difficulty,
            questions: passage.questions,
            vocabulary_notes: passage.vocabulary_notes
        };
    },

    submitAnswer(questionIndex, selectedOptionIndex) {
        if (!this.currentPassage) return null;

        const question = this.currentPassage.questions[questionIndex];
        if (!question) return null;

        const correct = selectedOptionIndex === question.correct;
        this.userAnswers[questionIndex] = selectedOptionIndex;
        this.questionsAnswered++;

        return {
            correct,
            correctIndex: question.correct,
            explanation: question.explanation,
            selectedIndex: selectedOptionIndex
        };
    },

    getResults() {
        if (!this.currentPassage) return null;

        const questions = this.currentPassage.questions;
        let correctCount = 0;
        const results = [];

        for (let i = 0; i < questions.length; i++) {
            const q = questions[i];
            const userAnswer = this.userAnswers[i];
            const isCorrect = userAnswer === q.correct;
            if (isCorrect) correctCount++;

            results.push({
                question: q.question,
                userAnswer: userAnswer !== undefined ? q.options[userAnswer] : '(未回答)',
                correctAnswer: q.options[q.correct],
                correct: isCorrect,
                explanation: q.explanation
            });
        }

        const score = questions.length > 0
            ? Math.round((correctCount / questions.length) * 100)
            : 0;

        // 记录阅读历史
        Storage.addReadingEntry({
            passageId: this.currentPassage.id,
            passageTitle: this.currentPassage.title,
            score: score,
            correctCount: correctCount,
            totalQuestions: questions.length
        });

        return {
            passageId: this.currentPassage.id,
            passageTitle: this.currentPassage.title,
            score: score,
            correctCount: correctCount,
            totalQuestions: questions.length,
            vocabularyNotes: this.currentPassage.vocabulary_notes,
            results: results
        };
    },

    getStats() {
        const history = Storage.getReadingHistory();
        const total = history.length;
        const totalCorrect = history.reduce((sum, h) => sum + (h.correctCount || 0), 0);
        const totalQuestions = history.reduce((sum, h) => sum + (h.totalQuestions || 0), 0);

        return {
            totalPassagesRead: total,
            totalCorrect: totalCorrect,
            totalQuestions: totalQuestions,
            percent: totalQuestions > 0 ? Math.round((totalCorrect / totalQuestions) * 100) : 0,
            lastRead: history.length > 0 ? history[history.length - 1] : null
        };
    }
};

window.ReadingEngine = ReadingEngine;

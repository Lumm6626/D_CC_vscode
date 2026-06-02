/**
 * 进阶级练习逻辑
 * 级别: Intermediate (Level 2)
 * 目标用户: 词汇量 3000-6000，雅思5.5-6.5分
 */

const IntermediateLevel = {
    name: 'intermediate',
    displayName: '进阶级',

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
            { type: 'fill填空', weight: 30, description: '选词填空' },
            { type: 'listen拼写', weight: 25, description: '听力拼写' },
            { type: 'match配对', weight: 25, description: '词组配对' },
            { type: 'word选择题', weight: 20, description: '词义选择' }
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
            level: 2,
            type: type
        };

        switch (type) {
            case 'fill填空':
                return this.createFillQuestion(word, base);
            case 'listen拼写':
                return this.createListenSpellingQuestion(word, base);
            case 'match配对':
                return this.createMatchQuestion(word, base);
            case 'word选择题':
                return this.createWordQuestion(word, base);
            default:
                return this.createFillQuestion(word, base);
        }
    },

    /**
     * 创建选词填空题目
     */
    createFillQuestion(word, base) {
        // 生成一个包含空格的句子
        const sentence = word.sentence || this.generateSentence(word);

        return {
            ...base,
            sentence: sentence.replace(word.word, '_____'),
            hint: word.word[0] + '_'.repeat(word.word.length - 1),
            options: this.generateFillOptions(word, 4),
            correctAnswer: word.word
        };
    },

    /**
     * 创建听力拼写题目
     */
    createListenSpellingQuestion(word, base) {
        return {
            ...base,
            audio: word.audio || word.word,
            hint: `单词长度: ${word.word.length}`,
            showHint: true,
            correctAnswer: word.word
        };
    },

    /**
     * 创建词组配对题目
     */
    createMatchQuestion(word, base) {
        return {
            ...base,
            word: word.word,
            phrase: word.phrase || this.generatePhrase(word),
            correctAnswer: word.meaning
        };
    },

    /**
     * 创建词义选择题
     */
    createWordQuestion(word, base) {
        return {
            ...base,
            question: `请选择"${word.word}"的正确含义`,
            options: this.generateMeaningOptions(word, 4),
            correctAnswer: word.meaning
        };
    },

    /**
     * 生成句子
     */
    generateSentence(word) {
        const templates = [
            `The researcher decided to ${word.word} the experiment.`,
            `The ${word.word} of the new policy took everyone by surprise.`,
            `Students must ${word.word} their assignments on time.`,
            `The ${word.word} between theory and practice is important.`,
            `We need to ${word.word} the problem systematically.`
        ];

        return templates[Math.floor(Math.random() * templates.length)];
    },

    /**
     * 生成词组/短语
     */
    generatePhrase(word) {
        const templates = [
            `${word.word} up`,
            `${word.word} down`,
            `${word.word} out`,
            `${word.word} in`,
            `${word.word} with`,
            `the ${word.word}`,
            `${word.word} and ${word.word}`
        ];

        return templates[Math.floor(Math.random() * templates.length)];
    },

    /**
     * 生成填空选项
     */
    generateFillOptions(targetWord, count) {
        const allWords = window.APP ? window.APP.getAllWords() : [];
        const options = [targetWord.word];

        const otherWords = allWords.filter(w => w.id !== targetWord.id);
        const shuffledOthers = this.shuffleArray(otherWords).slice(0, count - 1);

        for (const w of shuffledOthers) {
            if (options.length >= count) break;
            options.push(w.word);
        }

        while (options.length < count) {
            const fakeWord = this.generateFakeSimilarWord(targetWord.word);
            if (!options.includes(fakeWord)) {
                options.push(fakeWord);
            }
        }

        return this.shuffleArray(options);
    },

    /**
     * 生成相似假单词
     */
    generateFakeSimilarWord(original) {
        const fakeWords = [
            'abandon', 'ability', 'aboard', 'abroad', 'absent', 'absorb',
            'abstract', 'academic', 'access', 'accident', 'accompany', 'accomplish',
            'accurate', 'achieve', 'acquire', 'adapt', 'adequate', 'adjust',
            'advanced', 'advocate', 'affect', 'aggregate', 'allocate', 'alter'
        ];

        return fakeWords[Math.floor(Math.random() * fakeWords.length)];
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
            '建议，提倡', '表明，主张', '证实，论证', '归纳，总结'
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
        // 对于填空题，检查是否正确（忽略大小写）
        if (exercise.type === 'fill填空' || exercise.type === 'listen拼写') {
            const correct = answer.toLowerCase().trim() === exercise.correctAnswer.toLowerCase().trim();
            return {
                correct,
                feedback: correct ? '正确！' : `正确答案是: ${exercise.correctAnswer}`,
                correctAnswer: exercise.correctAnswer
            };
        }

        // 其他题型
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
    calculateReward(correct, streak) {
        let xp = 0;

        if (correct) {
            xp = 12; // 进阶比入门多2xp

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
            'fill填空': '在句子中选择正确的单词填空',
            'listen拼写': '听发音并拼写单词',
            'match配对': '将单词与其中文含义配对',
            'word选择题': '选择单词的正确含义'
        };
        return descriptions[type] || '选择正确答案';
    }
};

// 导出
window.IntermediateLevel = IntermediateLevel;
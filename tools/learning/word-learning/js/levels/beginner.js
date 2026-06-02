/**
 * 入门级练习逻辑
 * 级别: Beginner (Level 1)
 * 目标用户: 词汇量 0-3000，雅思4.5分以下
 */

const BeginnerLevel = {
    name: 'beginner',
    displayName: '入门级',

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
     * @returns {string}
     */
    getExerciseTypes() {
        return [
            { type: 'listen选择题', weight: 25, description: '听音选义' },
            { type: 'word选择题', weight: 25, description: '看词选义' },
            { type: 'listen拼写', weight: 20, description: '听音拼写' },
            { type: 'sentence填空', weight: 30, description: '句子选词填空' }
        ];
    },

    /**
     * 获取随机练习类型
     * @returns {string}
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
     * @param {Object} word - 单词对象
     * @param {string} type - 练习类型
     * @returns {Object}
     */
    createExercise(word, type) {
        const base = {
            id: word.id,
            word: word.word,
            meaning: word.meaning,
            level: 1,
            type: type
        };

        switch (type) {
            case 'listen选择题':
                return this.createListenQuestion(word, base);
            case 'word选择题':
                return this.createWordQuestion(word, base);
            case 'listen拼写':
                return this.createListenSpellingQuestion(word, base);
            case 'sentence填空':
                return this.createSentenceFillQuestion(word, base);
            default:
                return this.createListenQuestion(word, base);
        }
    },

    /**
     * 创建听音选词题目
     */
    createListenQuestion(word, base) {
        return {
            ...base,
            audio: word.audio || word.word,
            question: '请选择你听到的单词含义',
            options: this.generateMeaningOptions(word, 4),
            correctAnswer: word.meaning
        };
    },

    /**
     * 创建看词选义题目
     */
    createWordQuestion(word, base) {
        return {
            ...base,
            question: `请选择"${word.word}"的中文含义`,
            options: this.generateMeaningOptions(word, 4),
            correctAnswer: word.meaning
        };
    },

    /**
     * 创建听音拼写题目
     */
    createListenSpellingQuestion(word, base) {
        return {
            ...base,
            audio: word.audio || word.word,
            question: '请拼写你听到的单词',
            hint: `提示：${word.word[0]}${'_'.repeat(word.word.length - 1)} (${word.word.length}个字母)`,
            correctAnswer: word.word
        };
    },

    /**
     * 创建句子选词填空题目
     */
    createSentenceFillQuestion(word, base) {
        // 使用单词造句
        const sentence = this.generateSentence(word);
        const blankSentence = sentence.replace(word.word, '_____');

        return {
            ...base,
            sentence: blankSentence,
            question: `请选择正确的单词填入空白处`,
            options: this.generateWordOptionsForSentence(word, 4),
            correctAnswer: word.word
        };
    },

    /**
     * 生成例句
     */
    generateSentence(word) {
        const sentences = [
            `We need to ${word.word} the problem carefully.`,
            `The ${word.word} of this task is very important.`,
            `Students must ${word.word} their homework on time.`,
            `The teacher asked us to ${word.word} the lesson.`,
            `We should ${word.word} the new policy.`,
            `This book helps us ${word.word} the concept.`,
            `The company plans to ${word.word} a new system.`,
            `Please ${word.word} the form completely.`,
            `Scientists ${word.word} the experiment results.`,
            `We must ${word.word} our goals clearly.`
        ];
        return sentences[Math.floor(Math.random() * sentences.length)];
    },

    /**
     * 生成句子填空的选项（单词选项）
     */
    generateWordOptionsForSentence(targetWord, count) {
        const allWords = window.APP ? window.APP.getAllWords() : [];
        const options = [targetWord.word];

        // 从同级别单词中获取干扰项
        const otherWords = allWords.filter(w => w.id !== targetWord.id);
        const shuffledOthers = this.shuffleArray(otherWords).slice(0, count - 1);

        for (const w of shuffledOthers) {
            if (options.length >= count) break;
            options.push(w.word);
        }

        // 如果不够，用假单词补充
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

        // 从常见中文释义中获取干扰项
        const commonMeanings = [
            '执行，实施', '研究，调查', '发展，发育', '影响，作用',
            '创建，建立', '提供，给予', '接受，承认', '拒绝，否认',
            '帮助，援助', '支持，赞成', '反对，抵抗', '增加，增长',
            '减少，下降', '改变，转变', '保持，保留', '结束，终止',
            '开始，启动', '继续，持续', '完成，实现', '成功，完成',
            '学习，研究', '工作，职业', '生活，生命', '时间，时机',
            '原因，结果', '问题，议题', '方法，方式', '观点，看法',
            '重要，关键', '困难，挑战', '机会，可能性', '例子，示例'
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
     * @param {Object} exercise - 练习对象
     * @param {string} answer - 用户答案
     * @returns {Object} - { correct, feedback }
     */
    checkAnswer(exercise, answer) {
        let correct = false;

        // 拼写题：忽略大小写
        if (exercise.type === 'listen拼写' || exercise.type === 'sentence填空') {
            correct = answer.toLowerCase().trim() === exercise.correctAnswer.toLowerCase().trim();
        } else {
            // 选择题：精确匹配
            correct = answer === exercise.correctAnswer ||
                       (exercise.options && exercise.options.includes(exercise.correctAnswer));
        }

        return {
            correct,
            feedback: correct ? '正确！太棒了！' : `正确答案是: ${exercise.correctAnswer}`,
            correctAnswer: exercise.correctAnswer
        };
    },

    /**
     * 计算奖励
     */
    calculateReward(correct, streak) {
        let xp = 0;

        if (correct) {
            xp = 10;

            // 连胜加成
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
            'listen选择题': '听发音选择正确的中文含义',
            'word选择题': '选择单词的正确含义',
            'listen拼写': '听发音并拼写单词',
            'sentence填空': '在句子中选择正确的单词填空'
        };
        return descriptions[type] || '选择正确答案';
    }
};

// 导出
window.BeginnerLevel = BeginnerLevel;
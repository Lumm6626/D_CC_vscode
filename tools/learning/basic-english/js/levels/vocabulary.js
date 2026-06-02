/**
 * 步骤2-3：事物词 + 属性词学习引擎
 * 600 名词 + 150 形容词
 * 题型：词义匹配、反义词配对、分类排序、语境填空
 */

const VocabularyEngine = {
    words: [],
    thingWords: [],
    qualityWords: [],

    // 简单的图片词映射（使用 emoji 作为视觉辅助）
    picturableMap: {
        'apple': '\uD83C\uDF4E', 'orange': '\uD83C\uDF4A', 'banana': '\uD83C\uDF4C',
        'cat': '\uD83D\uDC08', 'dog': '\uD83D\uDC15', 'bird': '\uD83D\uDC26', 'fish': '\uD83D\uDC1F',
        'tree': '\uD83C\uDF33', 'flower': '\uD83C\uDF3C', 'sun': '\u2600\uFE0F', 'moon': '\uD83C\uDF19',
        'star': '\u2B50', 'water': '\uD83D\uDCA7', 'fire': '\uD83D\uDD25',
        'house': '\uD83C\uDFE0', 'book': '\uD83D\uDCD6', 'door': '\uD83D\uDEAA',
        'car': '\uD83D\uDE97', 'train': '\uD83D\uDE86', 'boat': '\uD83D\uDEA2', 'plane': '\u2708\uFE0F',
        'hand': '\u270B', 'foot': '\uD83E\uDDB6', 'eye': '\uD83D\uDC41', 'mouth': '\uD83D\uDC44',
        'head': '\uD83D\uDC64', 'heart': '\u2764\uFE0F', 'bread': '\uD83C\uDF5E', 'milk': '\uD83E\uDD5B',
        'egg': '\uD83E\uDD5A', 'cake': '\uD83C\uDF70', 'shoe': '\uD83D\uDC5F', 'hat': '\uD83C\uDFA9',
        'bed': '\uD83D\uDECF\uFE0F', 'table': '\uD83C\uDFE2', 'chair': '\uD83E\uDE91',
        'money': '\uD83D\uDCB0', 'clock': '\uD83D\uDD52', 'key': '\uD83D\uDD11',
        'ring': '\uD83D\uDC8D', 'knife': '\uD83D\uDD2A', 'box': '\uD83D\uDCE6',
        'cup': '\u2615', 'bottle': '\uD83C\uDF7E', 'pen': '\uD83D\uDD8A\uFE0F'
    },

    // 反义词对（用于配对练习）
    antonymPairs: [],

    init(words) {
        this.words = words || [];
        this.thingWords = this.words.filter(w => w.type === 'thing');
        this.qualityWords = this.words.filter(w => w.type === 'quality');
    },

    /**
     * @param {string} subStep - 'things' | 'qualities' | 'mixed'
     * @param {number} count
     */
    generateExercises(subStep = 'things', count = 10) {
        this.totalExercises = count;
        const progressMap = Storage.getWordProgress();

        let pool;
        switch (subStep) {
            case 'things':
                pool = this.thingWords;
                break;
            case 'qualities':
                pool = this.qualityWords;
                break;
            case 'mixed':
            default:
                pool = [...this.thingWords, ...this.qualityWords];
                break;
        }

        if (pool.length === 0) return [];

        const dailyTasks = SRS.getDailyTasks(pool, progressMap, Math.ceil(count / 2), Math.ceil(count / 2));
        let candidateWords = [...dailyTasks.newWords, ...dailyTasks.reviewWords];

        if (candidateWords.length < count) {
            const remaining = pool.filter(w => !candidateWords.find(c => c.id === w.id));
            candidateWords = [...candidateWords, ...SRS.shuffleArray(remaining)].slice(0, count);
        } else {
            candidateWords = SRS.shuffleArray(candidateWords).slice(0, count);
        }

        const exercises = [];
        for (const word of candidateWords) {
            exercises.push(this._createExercise(word, subStep));
        }

        return exercises;
    },

    _createExercise(word, subStep) {
        const types = ['meaning'];

        if (subStep === 'qualities' || word.type === 'quality') {
            types.push('antonym');
            types.push('context');
        }
        if (this.picturableMap[word.word]) {
            types.push('picture');
        }
        types.push('context');

        const type = types[Math.floor(Math.random() * types.length)];

        const base = {
            id: word.id,
            word: word.word,
            chinese: word.chinese,
            phonetic: word.phonetic,
            type: word.type,
            exerciseType: type,
            isOperation: false
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

            case 'picture':
                return {
                    ...base,
                    displayType: 'picture',
                    question: `这个图标"${this.picturableMap[word.word]}"对应的英文词是？`,
                    emoji: this.picturableMap[word.word],
                    options: SRS.generateMeaningOptions(word, this.words, 4),
                    correctAnswer: word.word
                };

            case 'antonym':
                // 需要反义词数据，这里为简单处理，生成词义匹配的变体
                const antonymHint = this._getAntonym(word);
                if (antonymHint) {
                    return {
                        ...base,
                        displayType: 'antonym',
                        question: `"${word.word}" 的反义词是？`,
                        options: this._generateAntonymOptions(word, antonymHint),
                        correctAnswer: antonymHint.word
                    };
                }
                // fall through to meaning
                return {
                    ...base,
                    displayType: 'meaning',
                    question: '这个词的中文意思是？',
                    options: SRS.generateMeaningOptions(word, this.words, 4),
                    correctAnswer: word.word
                };

            case 'context':
                const contextSentence = this._generateContextSentence(word);
                return {
                    ...base,
                    displayType: 'context',
                    question: `选择最合适的词填空："${contextSentence}"`,
                    contextSentence: contextSentence,
                    options: SRS.generateMeaningOptions(word, this.words, 4),
                    correctAnswer: word.word
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

    _getAntonym(word) {
        const antonymMap = {
            'good': 'bad', 'bad': 'good',
            'big': 'small', 'small': 'big',
            'high': 'low', 'low': 'high',
            'hot': 'cold', 'cold': 'hot',
            'fast': 'slow', 'slow': 'fast',
            'hard': 'soft', 'soft': 'hard',
            'heavy': 'light', 'light': 'heavy',
            'long': 'short', 'short': 'long',
            'new': 'old', 'old': 'new',
            'open': 'shut', 'shut': 'open',
            'rich': 'poor', 'poor': 'rich',
            'right': 'wrong', 'wrong': 'right',
            'strong': 'weak', 'weak': 'strong',
            'thick': 'thin', 'thin': 'thick',
            'true': 'false', 'false': 'true',
            'wide': 'narrow', 'narrow': 'wide',
            'happy': 'sad', 'sad': 'happy',
            'clean': 'dirty', 'dirty': 'clean',
            'dry': 'wet', 'wet': 'dry',
            'early': 'late', 'late': 'early',
            'full': 'empty', 'empty': 'full',
            'sweet': 'bitter', 'bitter': 'sweet',
            'black': 'white', 'white': 'black',
            'beautiful': 'ugly', 'ugly': 'beautiful',
            'safe': 'dangerous', 'dangerous': 'safe',
            'sharp': 'dull', 'dull': 'sharp',
            'smooth': 'rough', 'rough': 'smooth',
            'straight': 'bent', 'bent': 'straight',
            'tight': 'loose', 'loose': 'tight',
            'wise': 'foolish', 'foolish': 'wise',
            'young': 'old'
        };

        const antonymWord = antonymMap[word.word];
        if (antonymWord) {
            const antonymEntry = this.words.find(w => w.word === antonymWord);
            if (antonymEntry) {
                return { word: antonymEntry.word, chinese: antonymEntry.chinese };
            }
        }
        return null;
    },

    _generateAntonymOptions(word, antonym) {
        const options = [{ word: antonym.word, chinese: antonym.chinese }];
        const others = this.qualityWords.filter(w =>
            w.id !== word.id && w.word !== antonym.word
        );
        const shuffled = SRS.shuffleArray(others).slice(0, 3);
        for (const w of shuffled) {
            if (!options.find(o => o.chinese === w.chinese)) {
                options.push({ word: w.word, chinese: w.chinese });
            }
        }
        return SRS.shuffleArray(options);
    },

    _generateContextSentence(word) {
        const sentences = {
            'good': 'This is a very ___ book. I like it.',
            'bad': 'The weather is ___ today. It is raining.',
            'big': 'An elephant is a very ___ animal.',
            'small': 'An ant is a very ___ insect.',
            'high': 'The mountain is very ___.',
            'low': 'The table is too ___ for me.',
            'hot': 'The water is too ___ to drink.',
            'cold': 'The ice is very ___.',
            'fast': 'The car is going very ___.',
            'slow': 'The turtle is a ___ animal.',
            'hard': 'This stone is very ___.',
            'soft': 'The bed is very ___.',
            'long': 'The road is very ___.',
            'short': 'The pencil is too ___.',
            'new': 'I have a ___ dress.',
            'old': 'This building is very ___.',
            'clean': 'The room is very ___.',
            'dirty': 'The floor is ___.',
            'happy': 'She is very ___ today.',
            'sad': 'He felt ___ after hearing the news.',
            'beautiful': 'The garden is very ___.',
            'strong': 'He is a very ___ man.',
            'weak': 'After being sick, he felt ___.',
            'rich': 'He has a lot of money. He is ___.',
            'poor': 'She has no money. She is ___.',
            'wide': 'The river is very ___.',
            'narrow': 'The road through the mountain is ___.',
            'thick': 'The book is very ___.',
            'thin': 'The paper is ___.',
            'dry': 'The ground is ___ after days of sun.',
            'wet': 'My clothes are ___ from the rain.',
        };

        if (sentences[word.word]) {
            return sentences[word.word];
        }
        return `The word "${word.word}" is a ${word.type === 'thing' ? 'noun' : 'describing word'} that means "${word.chinese}".`;
    },

    checkAnswer(exercise, answer) {
        let correct = false;
        let feedback = '';

        switch (exercise.displayType) {
            case 'meaning':
            case 'picture':
                correct = answer === exercise.correctAnswer;
                feedback = correct
                    ? `正确！"${exercise.correctAnswer}" 的意思是"${exercise.chinese}"`
                    : `正确答案是 "${exercise.correctAnswer}"（${exercise.chinese}）`;
                break;

            case 'antonym':
                correct = answer === exercise.correctAnswer;
                feedback = correct
                    ? `正确！"${exercise.word}" 的反义词是 "${exercise.correctAnswer}"`
                    : `"${exercise.word}" 的反义词是 "${exercise.correctAnswer}"`;
                break;

            case 'context':
                correct = answer === exercise.correctAnswer;
                feedback = correct
                    ? `正确！句子应填入 "${exercise.correctAnswer}"`
                    : `正确答案是 "${exercise.correctAnswer}"。完整句子：${exercise.contextSentence.replace('___', exercise.correctAnswer)}`;
                break;

            default:
                correct = answer === exercise.correctAnswer;
                feedback = correct ? '正确！' : `正确答案是 "${exercise.correctAnswer}"`;
        }

        // 更新 SRS 进度
        const progress = Storage.getWordProgressById(exercise.id);
        const currentStrength = progress ? progress.strength : 0;
        const currentStreak = progress ? (progress.correctStreak || 0) : 0;
        const newStreak = correct ? currentStreak + 1 : 0;
        const newStrength = SRS.calculateStrength(currentStrength, correct, currentStreak);
        const nextReview = SRS.calculateNextReview(newStrength, correct, false);

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
            correctAnswer: exercise.correctAnswer
        };
    },

    getScore(type = 'all') {
        const progressMap = Storage.getWordProgress();
        let pool;
        switch (type) {
            case 'things': pool = this.thingWords; break;
            case 'qualities': pool = this.qualityWords; break;
            default: pool = [...this.thingWords, ...this.qualityWords]; break;
        }
        const total = pool.length;
        const mastered = pool.filter(w => {
            const p = progressMap[w.id];
            return p && p.strength >= 4;
        }).length;
        return { total, mastered, percent: total > 0 ? Math.round((mastered / total) * 100) : 0 };
    }
};

window.VocabularyEngine = VocabularyEngine;

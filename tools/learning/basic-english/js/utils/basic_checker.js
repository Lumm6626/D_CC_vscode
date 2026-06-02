/**
 * Basic English 翻译检查器
 *
 * 核心算法：分词 → 查不规则表 → 去词尾(-s/-ing/-ed/-ly/-er/-est) → 验证是否在 850 词内
 *
 * 输入: "The physician examined the patient."
 * 输出: { valid: false, words: [...], invalidWords: ["physician", "examined", "patient"], score: 57 }
 */

const BasicChecker = {
    basicWordSet: null,
    basicWordMap: null,

    /**
     * 不规则词映射表：变化形 → 原形
     * 覆盖 Basic English 动词和形容词的不规则变化
     */
    irregulars: {
        // 动词不规则过去式/过去分词
        'went': 'go', 'gone': 'go', 'goes': 'go',
        'came': 'come', 'comes': 'come',
        'got': 'get', 'gotten': 'get', 'gets': 'get',
        'gave': 'give', 'given': 'give', 'gives': 'give',
        'kept': 'keep', 'keeps': 'keep',
        'let': 'let', 'lets': 'let',
        'made': 'make', 'makes': 'make',
        'put': 'put', 'puts': 'put',
        'took': 'take', 'taken': 'take', 'takes': 'take',
        'seemed': 'seem', 'seems': 'seem',
        'was': 'be', 'were': 'be', 'been': 'be', 'being': 'be',
        'am': 'be', 'are': 'be', 'is': 'be',
        'did': 'do', 'done': 'do', 'does': 'do',
        'had': 'have', 'has': 'have', 'having': 'have',
        'said': 'say', 'says': 'say',
        'saw': 'see', 'seen': 'see', 'sees': 'see',
        'sent': 'send', 'sends': 'send',
        // 不规则比较级/最高级（Basic English 形容词）
        'better': 'good', 'best': 'good',
        'worse': 'bad', 'worst': 'bad',
        'more': 'much', 'most': 'much',
        'less': 'little', 'least': 'little',
        'farther': 'far', 'farthest': 'far',
        'further': 'far', 'furthest': 'far',
        // 其他常见不规则
        'felt': 'feel', 'fell': 'fall', 'fallen': 'fall',
        'thought': 'think', 'thoughts': 'thought',  // thought 不在 850 词中
        'knew': 'know', 'known': 'know',
        'told': 'tell',
        'began': 'begin', 'begun': 'begin',
        'brought': 'bring',
        'built': 'build',
        'bought': 'buy',
        'caught': 'catch',
        'chose': 'choose', 'chosen': 'choose',
        'drew': 'draw', 'drawn': 'draw',
        'drove': 'drive', 'driven': 'drive',
        'ate': 'eat', 'eaten': 'eat',
        'found': 'find',
        'flew': 'fly', 'flown': 'fly',
        'forgot': 'forget', 'forgotten': 'forget',
        'grew': 'grow', 'grown': 'grow',
        'heard': 'hear',
        'held': 'hold',
        'led': 'lead',
        'left': 'leave',
        'lost': 'lose',
        'meant': 'mean',
        'met': 'meet',
        'paid': 'pay',
        'ran': 'run',
        'showed': 'show', 'shown': 'show',
        'sat': 'sit',
        'slept': 'sleep',
        'spoke': 'speak', 'spoken': 'speak',
        'stood': 'stand',
        'swam': 'swim', 'swum': 'swim',
        'taught': 'teach',
        'threw': 'throw', 'thrown': 'throw',
        'understood': 'understand',
        'woke': 'wake', 'woken': 'wake',
        'wore': 'wear', 'worn': 'wear',
        'won': 'win',
        'wrote': 'write', 'written': 'write',
        'read': 'read',
        'cut': 'cut',
        'hit': 'hit',
        'hurt': 'hurt',
        'set': 'set',
        'shut': 'shut',
        'spent': 'spend',
        'cost': 'cost'
    },

    /**
     * 初始化检查器，加载 850 词集合
     * @param {Array} basicWords - basic_words.json 的数据
     */
    init(basicWords) {
        this.basicWordSet = new Set();
        this.basicWordMap = {};

        for (const entry of basicWords) {
            const word = entry.word.toLowerCase();
            this.basicWordSet.add(word);
            this.basicWordMap[word] = entry;

            // 对于操作词中的动词，添加常见规则屈折形式
            if (entry.type === 'operation' && entry.combinations && entry.combinations.length > 0) {
                this.basicWordSet.add(word + 's');
                this.basicWordSet.add(word + 'ing');
                this.basicWordSet.add(word + 'ed');
                // 去 e 再加 -ing/-ed
                if (word.endsWith('e')) {
                    this.basicWordSet.add(word.slice(0, -1) + 'ing');
                    this.basicWordSet.add(word.slice(0, -1) + 'ed');
                }
            }
        }

        // 常见合法屈折形式：即使 base form 不在 850 词，也接受
        this._addCommonInflections();
    },

    /**
     * 添加常见规则屈折形式到合法集
     */
    _addCommonInflections() {
        const commonPlurals = ['things', 'days', 'ways', 'times', 'men', 'women', 'children',
            'feet', 'teeth', 'mice', 'leaves', 'lives', 'knives', 'shelves'];
        for (const w of commonPlurals) {
            this.basicWordSet.add(w);
        }
    },

    /**
     * 分词：将句子拆分为单词数组（保留原始大小写以便展示）
     * @param {string} sentence
     * @returns {Array<{raw: string, lower: string, index: number}>}
     */
    tokenize(sentence) {
        const tokens = [];
        const regex = /[a-zA-Z]+('[a-zA-Z]+)?/g;
        let match;

        while ((match = regex.exec(sentence)) !== null) {
            tokens.push({
                raw: match[0],
                lower: match[0].toLowerCase(),
                index: match.index
            });
        }

        return tokens;
    },

    /**
     * 词形还原：去除常见英文字尾，返回基本形式
     * @param {string} word - 已小写化的单词
     * @returns {string} - 还原后的词干
     */
    lemmatize(word) {
        // 先查不规则表
        if (this.irregulars[word]) {
            return this.irregulars[word];
        }

        // 去除所有格 's
        if (word.endsWith("'s")) {
            word = word.slice(0, -2);
        }

        // 复合词：如 everybody → every + body（不在 850 也无妨）
        // nothing, something, anyone 等不在 Basic English 中

        // 去除副词后缀 -ly（但 careful→care 这类需要保留）
        if (word.endsWith('ly') && word.length > 4) {
            const stem = word.slice(0, -2);
            // 只有 -ly 是加在形容词后的才去除
            if (stem.endsWith('l')) {
                const doubleL = word.slice(0, -1);
                if (this.basicWordSet.has(doubleL)) return doubleL;
            }
            if (this.basicWordSet.has(stem)) return stem;
            // really → real (不在850), carefully → careful (不在850) 等
            // 不强制还原，如果 stem 不在集合中，保持原样
        }

        // 去除 -ing
        if (word.endsWith('ing') && word.length > 4) {
            let stem = word.slice(0, -3);
            if (this.basicWordSet.has(stem)) return stem;
            // 双写辅音：running → run
            if (stem.length > 2 && stem[stem.length - 1] === stem[stem.length - 2]) {
                const singleConsonant = stem.slice(0, -1);
                if (this.basicWordSet.has(singleConsonant)) return singleConsonant;
            }
            // 去 e：making → make
            if (this.basicWordSet.has(stem + 'e')) return stem + 'e';
        }

        // 去除 -ed
        if (word.endsWith('ed') && word.length > 3) {
            let stem = word.slice(0, -2);
            if (this.basicWordSet.has(stem)) return stem;
            // 双写辅音：stopped → stop
            if (stem.length > 2 && stem[stem.length - 1] === stem[stem.length - 2]) {
                const singleConsonant = stem.slice(0, -1);
                if (this.basicWordSet.has(singleConsonant)) return singleConsonant;
            }
            // -ied → -y：carried → carry
            if (stem.endsWith('i') && stem.length > 2) {
                const yForm = stem.slice(0, -1) + 'y';
                if (this.basicWordSet.has(yForm)) return yForm;
            }
            // 去 e：liked → like
            if (this.basicWordSet.has(stem + 'e')) return stem + 'e';
            // 只去 d：liked → like (stem 已是 like 去掉 d)
            const stemWithoutD = word.slice(0, -1);
            if (this.basicWordSet.has(stemWithoutD)) return stemWithoutD;
        }

        // 去除 -s / -es
        if (word.endsWith('es') && word.length > 4) {
            let stem = word.slice(0, -2);
            if (this.basicWordSet.has(stem)) return stem;
            // -ies → -y：carries → carry
            if (stem.endsWith('i') && stem.length > 2) {
                const yForm = stem.slice(0, -1) + 'y';
                if (this.basicWordSet.has(yForm)) return yForm;
            }
            // -ves → -f：leaves → leaf (但不规则表已处理)
        }
        if (word.endsWith('s') && !word.endsWith('ss') && word.length > 3) {
            let stem = word.slice(0, -1);
            if (this.basicWordSet.has(stem)) return stem;
        }

        // 去除 -er / -est 比较级
        if (word.endsWith('est') && word.length > 5) {
            let stem = word.slice(0, -3);
            if (this.basicWordSet.has(stem)) return stem;
            // 双写：biggest → big
            if (stem.length > 2 && stem[stem.length - 1] === stem[stem.length - 2]) {
                const single = stem.slice(0, -1);
                if (this.basicWordSet.has(single)) return single;
            }
        }
        if (word.endsWith('er') && word.length > 4) {
            let stem = word.slice(0, -2);
            if (this.basicWordSet.has(stem)) return stem;
            // 双写：bigger → big
            if (stem.length > 2 && stem[stem.length - 1] === stem[stem.length - 2]) {
                const single = stem.slice(0, -1);
                if (this.basicWordSet.has(single)) return single;
            }
            // -ier → -y：happier → happy
            if (stem.endsWith('i') && stem.length > 2) {
                const yForm = stem.slice(0, -1) + 'y';
                if (this.basicWordSet.has(yForm)) return yForm;
            }
        }

        return word;
    },

    /**
     * 检查句子是否仅使用 Basic English 词汇
     * @param {string} sentence - 用户输入的英文句子
     * @returns {Object} - { valid, words, invalidWords, score, suggestions }
     */
    checkSentence(sentence) {
        if (!this.basicWordSet) {
            return { valid: false, words: [], invalidWords: [], score: 0, suggestions: [], error: 'checker未初始化' };
        }

        const tokens = this.tokenize(sentence);
        const words = [];
        const invalidWords = [];
        const suggestions = [];

        for (const token of tokens) {
            const lemma = this.lemmatize(token.lower);
            const isBasic = this.basicWordSet.has(lemma) || this.basicWordSet.has(token.lower);

            words.push({
                raw: token.raw,
                lower: token.lower,
                lemma: lemma,
                isBasic: isBasic
            });

            if (!isBasic) {
                invalidWords.push({
                    word: token.raw,
                    lemma: lemma
                });

                // 查找替换建议
                const suggestion = this._findSuggestion(lemma);
                if (suggestion) {
                    suggestions.push({
                        original: token.raw,
                        suggestion: suggestion
                    });
                }
            }
        }

        const totalWords = tokens.length;
        const validCount = totalWords - invalidWords.length;
        const score = totalWords > 0 ? Math.round((validCount / totalWords) * 100) : 100;

        return {
            valid: invalidWords.length === 0,
            words: words,
            invalidWords: invalidWords,
            suggestions: suggestions,
            score: score,
            totalWords: totalWords,
            validCount: validCount
        };
    },

    /**
     * 查找替换建议（基于已知的 Basic English 等价词）
     */
    _findSuggestion(lemma) {
        // 常见复杂词 → Basic English 建议
        const suggestionMap = {
            'physician': 'doctor',
            'examined': 'looked at',
            'examine': 'look at',
            'patient': 'sick person',
            'departed': 'went away',
            'depart': 'go away',
            'purchase': 'buy',
            'obtain': 'get',
            'receive': 'get',
            'discover': 'come across',
            'encounter': 'come across',
            'require': 'need',
            'require': 'need',
            'attempt': 'try',
            'commence': 'start',
            'terminate': 'end',
            'construct': 'build',
            'destroy': 'break',
            'assist': 'help',
            'demonstrate': 'show',
            'indicate': 'point out',
            'observe': 'see',
            'perceive': 'see',
            'inquire': 'ask',
            'respond': 'answer',
            'request': 'ask for',
            'possess': 'have',
            'desire': 'want',
            'require': 'need',
            'permit': 'let',
            'allow': 'let',
            'remain': 'stay',
            'depart': 'go',
            'arrive': 'come',
            'cease': 'stop',
            'continue': 'go on',
            'complete': 'done',
            'sufficient': 'enough',
            'excellent': 'very good',
            'terrible': 'very bad',
            'enormous': 'very big',
            'tiny': 'very small',
            'beautiful': 'very good looking',
            'intelligent': 'clever',
            'difficult': 'hard',
            'simple': 'easy',
            'rapid': 'quick',
            'immediate': 'quick',
            'correct': 'right',
            'incorrect': 'wrong',
            'frequently': 'often',
            'immediately': 'at once',
            'gradually': 'slowly',
            'annually': 'every year',
            'perhaps': 'maybe',
            'however': 'but',
            'therefore': 'so',
            'additional': 'more',
            'numerous': 'many',
            'various': 'different',
            'identical': 'same',
            'entire': 'whole',
            'portion': 'part',
            'quantity': 'amount',
            'substance': 'stuff',
            'vehicle': 'car',
            'residence': 'house',
            'automobile': 'car',
            'canine': 'dog',
            'feline': 'cat',
            'physician': 'doctor',
            'attorney': 'lawyer',
            'educator': 'teacher',
            'infant': 'baby',
            'adolescent': 'young person',
            'individual': 'person',
            'gentleman': 'man',
            'female': 'woman',
            'male': 'man',
            'human': 'person',
            'conversation': 'talk',
            'information': 'news',
            'knowledge': 'knowledge',
            'education': 'teaching',
            'transportation': 'transport',
            'construction': 'building',
            'destruction': 'destruction',
            'development': 'growth',
            'environment': 'surroundings',
            'temperature': 'heat',
            'precipitation': 'rain',
            'illumination': 'light',
            'nutrition': 'food',
            'beverage': 'drink',
            'automobile': 'car',
            'merchandise': 'goods',
            'currency': 'money',
            'compensation': 'pay',
            'occupation': 'work',
            'profession': 'work',
            'colleague': 'work friend',
            'acquaintance': 'friend',
            'companion': 'friend',
            'relative': 'family',
            'spouse': 'wife or husband',
            'sibling': 'brother or sister',
            'parent': 'father or mother',
            'offspring': 'child',
            'ancestor': 'father of fathers',
            'descendant': 'child of children'
        };

        return suggestionMap[lemma] || null;
    },

    /**
     * 检查单个词是否在 Basic English 中
     * @param {string} word
     * @returns {boolean}
     */
    isBasicWord(word) {
        if (!this.basicWordSet) return false;
        const lower = word.toLowerCase();
        const lemma = this.lemmatize(lower);
        return this.basicWordSet.has(lemma) || this.basicWordSet.has(lower);
    }
};

window.BasicChecker = BasicChecker;

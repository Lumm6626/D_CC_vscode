/**
 * TTS 语音模块
 * 使用 Web Speech API
 */

const TTS = {
    isSpeaking: false,
    defaultSpeed: 1,
    defaultLang: 'en-US',

    /**
     * 初始化 TTS
     */
    init() {
        if (!('speechSynthesis' in window)) {
            console.warn('Web Speech API not supported');
            return false;
        }
        return true;
    },

    /**
     * 朗读文本
     * @param {string} text - 要朗读的文本
     * @param {Object} options - 配置选项
     */
    speak(text, options = {}) {
        return new Promise((resolve, reject) => {
            if (!('speechSynthesis' in window)) {
                reject(new Error('Speech API not supported'));
                return;
            }

            // 取消之前的朗读
            this.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = options.lang || this.defaultLang;
            utterance.rate = options.speed || this.defaultSpeed;
            utterance.pitch = options.pitch || 1;
            utterance.volume = options.volume || 1;

            utterance.onstart = () => {
                this.isSpeaking = true;
            };

            utterance.onend = () => {
                this.isSpeaking = false;
                resolve();
            };

            utterance.onerror = (e) => {
                this.isSpeaking = false;
                reject(e);
            };

            speechSynthesis.speak(utterance);
        });
    },

    /**
     * 朗读单词
     * @param {string} word - 单词
     * @param {Object} options - 配置选项
     */
    speakWord(word, options = {}) {
        return this.speak(word, {
            lang: 'en-US',
            ...options
        });
    },

    /**
     * 朗读中文
     * @param {string} text - 中文文本
     * @param {Object} options - 配置选项
     */
    speakChinese(text, options = {}) {
        return this.speak(text, {
            lang: 'zh-CN',
            ...options
        });
    },

    /**
     * 停止朗读
     */
    cancel() {
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
        }
        this.isSpeaking = false;
    },

    /**
     * 暂停朗读
     */
    pause() {
        if ('speechSynthesis' in window) {
            speechSynthesis.pause();
        }
    },

    /**
     * 继续朗读
     */
    resume() {
        if ('speechSynthesis' in window) {
            speechSynthesis.resume();
        }
    },

    /**
     * 检查是否正在朗读
     */
    isSpeaking() {
        return this.isSpeaking;
    },

    /**
     * 获取可用的语音列表
     */
    getVoices() {
        return new Promise((resolve) => {
            if (!('speechSynthesis' in window)) {
                resolve([]);
                return;
            }

            const voices = speechSynthesis.getVoices();
            if (voices.length > 0) {
                resolve(voices);
            } else {
                speechSynthesis.onvoiceschanged = () => {
                    resolve(speechSynthesis.getVoices());
                };
            }
        });
    },

    /**
     * 获取英语语音
     */
    async getEnglishVoice() {
        const voices = await this.getVoices();
        // 优先选择英语语音
        const englishVoices = voices.filter(v => v.lang.startsWith('en'));
        if (englishVoices.length > 0) {
            // 尝试选择高质量语音
            const preferred = englishVoices.find(v => v.name.includes('Google')) ||
                            englishVoices.find(v => v.name.includes('Microsoft')) ||
                            englishVoices[0];
            return preferred;
        }
        return null;
    }
};

// 导出
window.TTS = TTS;
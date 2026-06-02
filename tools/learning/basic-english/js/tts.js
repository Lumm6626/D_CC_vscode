/**
 * TTS 语音模块
 * 使用 Web Speech API
 */

const TTS = {
    isSpeaking: false,
    defaultSpeed: 1,
    defaultLang: 'en-US',

    init() {
        if (!('speechSynthesis' in window)) {
            console.warn('Web Speech API not supported');
            return false;
        }
        return true;
    },

    speak(text, options = {}) {
        return new Promise((resolve, reject) => {
            if (!('speechSynthesis' in window)) {
                reject(new Error('Speech API not supported'));
                return;
            }

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

    speakWord(word, options = {}) {
        return this.speak(word, {
            lang: 'en-US',
            ...options
        });
    },

    speakChinese(text, options = {}) {
        return this.speak(text, {
            lang: 'zh-CN',
            ...options
        });
    },

    cancel() {
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
        }
        this.isSpeaking = false;
    },

    pause() {
        if ('speechSynthesis' in window) {
            speechSynthesis.pause();
        }
    },

    resume() {
        if ('speechSynthesis' in window) {
            speechSynthesis.resume();
        }
    },

    isSpeaking() {
        return this.isSpeaking;
    },

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

    async getEnglishVoice() {
        const voices = await this.getVoices();
        const englishVoices = voices.filter(v => v.lang.startsWith('en'));
        if (englishVoices.length > 0) {
            const preferred = englishVoices.find(v => v.name.includes('Google')) ||
                            englishVoices.find(v => v.name.includes('Microsoft')) ||
                            englishVoices[0];
            return preferred;
        }
        return null;
    }
};

window.TTS = TTS;

// Google Gemini AI Service
class GeminiService {
    constructor(sessionToken, config) {
        this.sessionToken = sessionToken;
        this.config = config;
        this.baseUrl = config.baseUrl;
        this.model = config.model;
        this.customPrompts = {
            summarization: null,
            translation: null
        };
    }

    async generateContent(prompt, systemInstruction = null, retries = 2) {
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const requestBody = {
                    contents: [{
                        parts: [{ text: prompt }]
                    }],
                    generationConfig: {
                        temperature: 0.7,
                        topK: 40,
                        topP: 0.95,
                        maxOutputTokens: 1024,
                    }
                };

                if (systemInstruction) {
                    requestBody.systemInstruction = {
                        parts: [{ text: systemInstruction }]
                    };
                }

                const response = await fetch('/api/gemini/generate', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.sessionToken}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        model: this.model,
                        request_body: requestBody
                    })
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Gemini API error: ${response.status} ${response.statusText} - ${errorText}`);
                }

                const data = await response.json();

                if (data.candidates && data.candidates[0] && data.candidates[0].content) {
                    return data.candidates[0].content.parts[0].text;
                } else {
                    throw new Error('Invalid response format from Gemini API');
                }
            } catch (error) {
                console.error(`Gemini API error (attempt ${attempt + 1}):`, error);

                if (attempt === retries) {
                    throw error;
                }

                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
            }
        }
    }

    async summarizeTranscript(transcript) {
        const transcriptText = Array.isArray(transcript)
            ? transcript.map(entry => `${entry.speaker}: ${entry.text}`).join('\n')
            : transcript;

        let systemInstruction = this.customPrompts.summarization;
        let prompt;

        if (systemInstruction) {
            prompt = systemInstruction.replace('{transcript}', transcriptText);
            systemInstruction = null;
        } else {
            prompt = `Please provide a concise summary of the following meeting transcript. Focus on key points, decisions made, and action items:

${transcriptText}

Summary:`;
            systemInstruction = "You are an expert meeting summarizer. Provide clear, concise summaries that capture the most important information from meeting transcripts.";
        }

        return await this.generateContent(prompt, systemInstruction);
    }

    async translateText(text, targetLanguage) {
        const languageNames = {
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'my': 'Myanmar (Burmese)',
            'hi': 'Hindi',
            'bn': 'Bengali'
        };

        const targetLangName = languageNames[targetLanguage] || targetLanguage;
        let systemInstruction = this.customPrompts.translation;
        let prompt;

        if (systemInstruction) {
            prompt = systemInstruction
                .replace('{text}', text)
                .replace('{target_language}', targetLangName);
            systemInstruction = null;
        } else {
            prompt = `Translate the following text to ${targetLangName}. Ensure proper Unicode encoding and maintain cultural context:

${text}

Translation:`;

            systemInstruction = `You are a professional translator with expertise in multiple writing systems including Latin, Devanagari, Bengali, and Myanmar scripts. Provide accurate translations while maintaining the original meaning, context, and proper Unicode formatting. For Myanmar, Hindi, and Bengali translations, ensure correct script rendering and cultural appropriateness.`;
        }

        return await this.generateContent(prompt, systemInstruction);
    }

    async extractKeywords(transcript) {
        const transcriptText = Array.isArray(transcript)
            ? transcript.map(entry => entry.text).join(' ')
            : transcript;

        const prompt = `Extract the most important keywords and key phrases from the following meeting transcript. Return only the keywords/phrases, separated by commas:

${transcriptText}

Keywords:`;

        const systemInstruction = "You are an expert at extracting key terms and phrases from meeting transcripts. Focus on important topics, decisions, and action items.";

        const result = await this.generateContent(prompt, systemInstruction);
        return result.split(',').map(keyword => keyword.trim()).filter(keyword => keyword.length > 0);
    }

    async loadCustomPrompts() {
        try {
            const response = await fetch('/api/prompts', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.sessionToken}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.customPrompts = {
                    summarization: data.summarization || null,
                    translation: data.translation || null
                };
                return this.customPrompts;
            }
        } catch (error) {
            console.error('Failed to load custom prompts:', error);
        }
        return null;
    }

    async saveCustomPrompt(promptType, promptText) {
        try {
            const response = await fetch(`/api/prompts/${promptType}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.sessionToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt_type: promptType,
                    prompt_text: promptText
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.customPrompts[promptType] = promptText;
                return { success: true, message: data.message };
            } else {
                const error = await response.json();
                return { success: false, error: error.error };
            }
        } catch (error) {
            console.error('Failed to save custom prompt:', error);
            return { success: false, error: 'Network error occurred' };
        }
    }

    async validateCustomPrompt(promptType, promptText) {
        try {
            const response = await fetch(`/api/prompts/${promptType}/validate`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.sessionToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt_type: promptType,
                    prompt_text: promptText
                })
            });

            if (response.ok) {
                const data = await response.json();
                return { valid: data.valid, message: data.message, missing_placeholders: data.missing_placeholders };
            } else {
                const error = await response.json();
                return { valid: false, message: error.error };
            }
        } catch (error) {
            console.error('Failed to validate custom prompt:', error);
            return { valid: false, message: 'Network error occurred' };
        }
    }

    async resetCustomPrompt(promptType) {
        try {
            const response = await fetch(`/api/prompts/${promptType}/reset`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.sessionToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt_type: promptType
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.customPrompts[promptType] = null;
                return { success: true, message: data.message, default_prompt: data.default_prompt };
            } else {
                const error = await response.json();
                return { success: false, error: error.error };
            }
        } catch (error) {
            console.error('Failed to reset custom prompt:', error);
            return { success: false, error: 'Network error occurred' };
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GeminiService;
} else if (typeof window !== 'undefined') {
    window.GeminiService = GeminiService;
}
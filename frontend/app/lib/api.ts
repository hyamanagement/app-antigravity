import axios from "axios";

// Configura l'URL del backend. 
// In sviluppo locale è http://localhost:8000
const API = axios.create({
    baseURL: "http://localhost:8000/api",
});

export interface TranscriptResponse {
    title: string;
    channel: string;
    transcript: string;
    paraphrase?: string;
    translation?: string;
    tags?: string[];
    video_url: string;
    thumbnail_url?: string;
    frame_urls?: string[];
    platform?: string;
}

export interface ResearchResponse {
    topics: string[];
    market_research: {
        topic: string;
        research?: string;
        error?: string;
    }[];
}

export interface ScriptResponse {
    script_content: string;
}

export interface TopicGenerateResponse {
    topics: string[];
    market_research: {
        topic: string;
        research?: string;
        error?: string;
    }[];
    script_content: string;
}

export interface TranslateResponse {
    translated_text: string;
}

export const api = {
    transcribe: async (url: string) => {
        const { data } = await API.post<TranscriptResponse>("/transcribe", { url });
        return data;
    },

    transcribeStream: async (url: string, targetLanguage: string = "en", onEvent: (event: any) => void) => {
        const response = await fetch("http://localhost:8000/api/transcribe-stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ url, target_language: targetLanguage }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `Request failed with status ${response.status}`);
        }

        if (!response.body) return;
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (line.trim()) {
                    try {
                        const event = JSON.parse(line);
                        onEvent(event);
                    } catch (e) {
                        console.error("Error parsing stream line:", e);
                    }
                }
            }
        }
    },

    research: async (transcript: string, targetLanguage: string = "it") => {
        const { data } = await API.post<ResearchResponse>("/research", { transcript, target_language: targetLanguage });
        return data;
    },

    generate: async (transcript: string, researchData: any[], targetLanguage: string = "it", tone: string = "educational") => {
        const { data } = await API.post<ScriptResponse>("/generate", {
            transcript,
            research_data: researchData,
            target_language: targetLanguage,
            tone
        });
        return data;
    },

    generateFromTopic: async (topic: string, tone: string = "educational", targetLanguage: string = "it") => {
        const { data } = await API.post<TopicGenerateResponse>("/generate-from-topic", {
            topic,
            tone,
            target_language: targetLanguage
        });
        return data;
    },

    translate: async (text: string, target_language: string) => {
        const { data } = await API.post<TranslateResponse>("/translate", {
            text,
            target_language
        });
        return data;
    },

    translateStream: async (text: string, target_language: string, onChunk: (chunk: string) => void) => {
        const response = await fetch("http://localhost:8000/api/translate-stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ text, target_language }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `Request failed with status ${response.status}`);
        }

        if (!response.body) return;
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            onChunk(chunk);
        }
    }
};

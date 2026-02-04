"use client";

import { Language } from "@/lib/translations";

interface LanguageSelectorProps {
    currentLang: Language;
    onLanguageChange: (lang: Language) => void;
    disabled?: boolean;
}

export const LanguageSelector = ({ currentLang, onLanguageChange, disabled }: LanguageSelectorProps) => {
    return (
        <select
            value={currentLang}
            onChange={(e) => onLanguageChange(e.target.value as Language)}
            disabled={disabled}
            className={`bg-slate-900 border border-slate-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
            <option value="it">🇮🇹 Italian</option>
            <option value="en">🇺🇸 English</option>
            <option value="ru">🇷🇺 Russian</option>
            <option value="fr">🇫🇷 French</option>
            <option value="zh">🇨🇳 Chinese</option>
        </select>
    );
};

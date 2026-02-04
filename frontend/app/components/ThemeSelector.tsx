"use client";

export type Theme = "light" | "dark";

interface ThemeSelectorProps {
    currentTheme: Theme;
    onThemeChange: (theme: Theme) => void;
}

export const ThemeSelector = ({ currentTheme, onThemeChange }: ThemeSelectorProps) => {
    return (
        <select
            value={currentTheme}
            onChange={(e) => onThemeChange(e.target.value as Theme)}
            className="bg-slate-900 border border-slate-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5"
        >
            <option value="dark">🌑 Dark</option>
            <option value="light">☀️ Light</option>
        </select>
    );
};

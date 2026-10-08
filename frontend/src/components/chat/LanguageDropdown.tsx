import { useState, useRef, useEffect, useCallback, useId } from "react";
import { Languages, ChevronDown, Check } from "lucide-react";

export interface LanguageOption {
  code: string;
  name: string;
  native: string;
}

export const SUPPORTED_CHAT_LANGUAGES: LanguageOption[] = [
  { code: "en", name: "English", native: "English" },
  { code: "hi", name: "Hindi", native: "हिंदी" },
  { code: "ml", name: "Malayalam", native: "മലയാളം" },
  { code: "mr", name: "Marathi", native: "मराठी" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ" },
  { code: "bn", name: "Bengali", native: "বাংলা" },
  { code: "gu", name: "Gujarati", native: "ગુજરાતી" },
  { code: "pa", name: "Punjabi", native: "ਪੰਜਾਬੀ" },
  { code: "ur", name: "Urdu", native: "اردو" },
];

interface LanguageDropdownProps {
  value: string;
  onChange: (code: string) => void;
  className?: string;
}

export function LanguageDropdown({
  value,
  onChange,
  className = "",
}: LanguageDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const listboxId = useId();

  const currentOption =
    SUPPORTED_CHAT_LANGUAGES.find((l) => l.code.toLowerCase() === value.toLowerCase()) ||
    SUPPORTED_CHAT_LANGUAGES[0];

  const handleSelect = useCallback(
    (code: string) => {
      onChange(code);
      setIsOpen(false);
      triggerRef.current?.focus();
    },
    [onChange]
  );

  // Close when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (e: MouseEvent | TouchEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
    };
  }, [isOpen]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        setIsOpen(true);
        const idx = SUPPORTED_CHAT_LANGUAGES.findIndex(
          (l) => l.code === currentOption.code
        );
        setHighlightedIndex(idx >= 0 ? idx : 0);
      }
      return;
    }

    if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev < SUPPORTED_CHAT_LANGUAGES.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev > 0 ? prev - 1 : SUPPORTED_CHAT_LANGUAGES.length - 1
      );
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (
        highlightedIndex >= 0 &&
        highlightedIndex < SUPPORTED_CHAT_LANGUAGES.length
      ) {
        handleSelect(SUPPORTED_CHAT_LANGUAGES[highlightedIndex].code);
      }
    } else if (e.key === "Tab") {
      setIsOpen(false);
    }
  };

  return (
    <div
      ref={containerRef}
      className={`relative inline-block text-left ${className}`}
      onKeyDown={handleKeyDown}
    >
      {/* Trigger Button */}
      <button
        ref={triggerRef}
        type="button"
        onClick={() => {
          setIsOpen((prev) => !prev);
          if (!isOpen) {
            const idx = SUPPORTED_CHAT_LANGUAGES.findIndex(
              (l) => l.code === currentOption.code
            );
            setHighlightedIndex(idx >= 0 ? idx : 0);
          }
        }}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-label={`Target language: ${currentOption.name}`}
        className="flex items-center gap-1 sm:gap-1.5 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 hover:border-teal-500/50 dark:hover:border-teal-500/50 px-2 sm:px-2.5 py-1.5 rounded-xl text-xs text-slate-800 dark:text-slate-100 shadow-2xs hover:shadow-xs transition-all cursor-pointer min-h-[36px]"
        title="Select target language for message translation"
      >
        <Languages className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400 shrink-0" />
        <span className="hidden md:inline text-[11px] text-slate-500 dark:text-slate-400 font-medium">
          Translate:
        </span>
        <span className="font-semibold text-[11px] sm:text-xs text-slate-900 dark:text-white">
          {currentOption.code.toUpperCase()}
          <span className="hidden sm:inline text-slate-500 dark:text-slate-400 font-normal ml-1">
            ({currentOption.native})
          </span>
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 dark:text-slate-500 transition-transform duration-200 shrink-0 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Accessible Dark-Themed Dropdown Panel */}
      {isOpen && (
        <div
          id={listboxId}
          role="listbox"
          aria-label="Target translation language"
          className="absolute right-0 mt-1.5 w-52 sm:w-60 max-h-72 overflow-y-auto rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-1.5 z-50 focus:outline-none backdrop-blur-md animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 border-b border-slate-100 dark:border-slate-800/80 mb-1">
            Select Language
          </div>

          {SUPPORTED_CHAT_LANGUAGES.map((lang, idx) => {
            const isSelected =
              lang.code.toLowerCase() === currentOption.code.toLowerCase();
            const isHighlighted = idx === highlightedIndex;

            return (
              <div
                key={lang.code}
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(lang.code)}
                onMouseEnter={() => setHighlightedIndex(idx)}
                className={`group flex items-center justify-between px-2.5 py-2 rounded-xl text-xs cursor-pointer transition-colors min-h-[38px] ${
                  isSelected
                    ? "bg-teal-50 dark:bg-teal-950/60 text-teal-800 dark:text-teal-300 font-bold"
                    : isHighlighted
                    ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white font-medium"
                    : "text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span
                    className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded-md ${
                      isSelected
                        ? "bg-teal-200/60 dark:bg-teal-900/60 text-teal-900 dark:text-teal-200 font-bold"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                    }`}
                  >
                    {lang.code.toUpperCase()}
                  </span>
                  <span className="truncate">{lang.name}</span>
                  <span className="text-[11px] text-slate-400 dark:text-slate-500 truncate">
                    ({lang.native})
                  </span>
                </div>

                {isSelected && (
                  <Check className="w-4 h-4 text-teal-600 dark:text-teal-400 shrink-0 ml-1.5" />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

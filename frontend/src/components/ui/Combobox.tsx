import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface Option {
  value: string;
  label: string;
}

interface ComboboxProps {
  items: ReadonlyArray<string | Option>;
  value?: string | null;
  onChange: (value: string | null) => void;
  placeholder?: string;
  className?: string;
  searchable?: boolean;
  onBlur?: () => void;
  ariaInvalid?: boolean;
}

export default function Combobox({
  items,
  value = null,
  onChange,
  placeholder = "Select...",
  className = "",
  searchable = true,
  onBlur,
  ariaInvalid,
}: ComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [coords, setCoords] = useState<{ top: number; left: number; width: number } | null>(null);

  const normalized: Option[] = items.map((it) => (typeof it === "string" ? { value: it, label: it } : it));
  const filtered = query.trim() === "" ? normalized : normalized.filter((o) => o.label.toLowerCase().includes(query.toLowerCase()));

  // When closed, show the selected label in the input for trigger-like behavior
  const selectedLabel = value ? (normalized.find((o) => o.value === value)?.label ?? "") : "";

  useEffect(() => {
    if (!open) setActiveIndex(-1);
  }, [open]);

  useEffect(() => {
    function updatePosition() {
      if (open && containerRef.current) {
        const r = containerRef.current.getBoundingClientRect();
        setCoords({ top: r.bottom + window.scrollY + 8, left: r.left + window.scrollX, width: r.width });
      }
    }
    if (open) {
      updatePosition();
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
    }
    return () => {
      window.removeEventListener('scroll', updatePosition, true);
      window.removeEventListener('resize', updatePosition);
    };
  }, [open]);

  useEffect(() => {
    // clamp activeIndex
    if (activeIndex >= filtered.length) setActiveIndex(filtered.length - 1);
  }, [filtered.length, activeIndex]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (open && activeIndex >= 0 && filtered[activeIndex]) {
        selectValue(filtered[activeIndex].value);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  function selectValue(v: string | null) {
    setQuery("");
    setOpen(false);
    onChange(v);
  }

  function openList() {
    setOpen(true);
    // Keep caret ready for search; do not rely solely on focus (already-focused inputs
    // will not re-fire onFocus after a selection).
    if (searchable) {
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }

  function toggleList() {
    if (open) {
      setOpen(false);
      return;
    }
    openList();
  }

  return (
    <div ref={containerRef} className={`ui-select ${className}`}>
      <input
        ref={inputRef}
        role="combobox"
        aria-expanded={open}
        aria-controls="combobox-list"
        aria-autocomplete="list"
        aria-invalid={ariaInvalid}
        className="input"
        value={open ? query : (selectedLabel || query)}
        onChange={(e) => {
          if (searchable) {
            setQuery(e.target.value);
            setOpen(true);
          }
        }}
        readOnly={!searchable}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          setTimeout(() => setOpen(false), 120);
          onBlur?.();
        }}
        onClick={() => {
          // After a selection the input often keeps focus, so onFocus does not fire again.
          // Always reopen when closed; non-searchable also toggles closed→open via click.
          if (!open) {
            openList();
          } else if (!searchable) {
            setOpen(false);
          }
        }}
      />
      <button
        type="button"
        className="ui-select-arrow"
        tabIndex={-1}
        aria-label="Toggle options"
        onMouseDown={(e) => {
          e.preventDefault();
          toggleList();
        }}
      >
        ▾
      </button>

      {open && coords ? createPortal(
        <ul id="combobox-list" role="listbox" ref={listRef} className="combobox-list" style={{ position: 'absolute', top: coords.top, left: coords.left, minWidth: coords.width, zIndex: 9999 }}>
          {filtered.length === 0 ? (
            <li className="combobox-item combobox-item-empty">No results</li>
          ) : (
            filtered.map((opt, idx) => (
              <li
                key={opt.value}
                role="option"
                aria-selected={value === opt.value}
                className={`combobox-item${idx === activeIndex ? " combobox-item-active" : ""}${value === opt.value ? " combobox-item-selected" : ""}`}
                onMouseDown={(e) => { e.preventDefault(); selectValue(opt.value); }}
                onMouseEnter={() => setActiveIndex(idx)}
              >
                {opt.label}
              </li>
            ))
          )}
        </ul>,
        document.body
      ) : null}
    </div>
  );
}

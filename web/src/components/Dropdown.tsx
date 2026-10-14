import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

/** A non-modal disclosure for action buttons or account controls. */
export default function Dropdown({ label, name, children, className = '', closeOnAction = false }: {
  label: ReactNode; name: string; children: ReactNode; className?: string; closeOnAction?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  function close() { setOpen(false); trigger.current?.focus(); }
  useEffect(() => {
    if (!open) return;
    panel.current?.focus();
    function outside(event: Event) {
      if (!(event.target instanceof Node) || root.current?.contains(event.target)) return;
      if (event.type === 'pointerdown' && panel.current?.contains(document.activeElement)) {
        setTimeout(() => {
          if (document.activeElement === document.body || panel.current?.contains(document.activeElement)) trigger.current?.focus();
        }, 0);
      }
      setOpen(false);
    }
    function escape(event: KeyboardEvent) {
      if (event.key !== 'Escape') return;
      event.stopImmediatePropagation();
      close();
    }
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', outside);
    document.addEventListener('keydown', escape, true);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('focusin', outside);
      document.removeEventListener('keydown', escape, true);
    };
  }, [open]);
  return <div ref={root} className={`dropdown ${className}`}>
    <button ref={trigger} className="dropdown-trigger" type="button" aria-label={name} aria-expanded={open} aria-controls={id} onClick={() => setOpen(value => !value)}>{label}<span className="dropdown-chevron" aria-hidden="true">⌄</span></button>
    <div ref={panel} id={id} className="dropdown-panel" role="group" aria-label={`${name}內容`} hidden={!open} tabIndex={-1}
      onClickCapture={event => { if (closeOnAction && event.target instanceof Element && event.target.closest('button:not(:disabled)')) close(); }}>{children}</div>
  </div>;
}

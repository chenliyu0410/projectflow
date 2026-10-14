import { useEffect } from 'react';

// Preserve native scrolling and dragging; change only the thumb colour.
export default function useScrollActivity() {
  useEffect(() => {
    const timers = new Map<HTMLElement, ReturnType<typeof setTimeout>>();
    function reveal(element: HTMLElement) {
      clearTimeout(timers.get(element));
      element.dataset.scrollActive = 'true';
      timers.set(element, setTimeout(() => {
        delete element.dataset.scrollActive;
        timers.delete(element);
      }, 900));
    }
    function scrolling(event: Event) {
      const element = event.target === document ? document.documentElement : event.target;
      if (element instanceof HTMLElement) reveal(element);
    }
    function edge(event: PointerEvent) {
      if (event.pointerType === 'touch') return;
      let element = event.target instanceof HTMLElement ? event.target : null;
      while (element) {
        const box = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        const vertical = element.scrollHeight > element.clientHeight && /auto|scroll/.test(style.overflowY) && event.clientX >= box.right - 14;
        const horizontal = element.scrollWidth > element.clientWidth && /auto|scroll/.test(style.overflowX) && event.clientY >= box.bottom - 14;
        if (vertical || horizontal) { reveal(element); break; }
        element = element.parentElement;
      }
    }
    document.addEventListener('scroll', scrolling, { capture: true, passive: true });
    document.addEventListener('pointermove', edge, { passive: true });
    return () => {
      document.removeEventListener('scroll', scrolling, true);
      document.removeEventListener('pointermove', edge);
      timers.forEach((timer, element) => { clearTimeout(timer); delete element.dataset.scrollActive; });
    };
  }, []);
}

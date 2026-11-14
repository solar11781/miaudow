// Test setup: jsdom lacks matchMedia, IntersectionObserver, ResizeObserver and dialog methods; minimal stand-ins.
window.matchMedia ??= ((query: string) => ({
  matches: false, media: query, onchange: null,
  addEventListener: () => undefined, removeEventListener: () => undefined,
  addListener: () => undefined, removeListener: () => undefined, dispatchEvent: () => false,
})) as typeof window.matchMedia;

class Observer { observe() { /* noop */ } unobserve() { /* noop */ } disconnect() { /* noop */ } }
const w = window as unknown as Record<string, unknown>;
w.IntersectionObserver ??= Observer;
w.ResizeObserver ??= Observer;

if (typeof HTMLDialogElement !== 'undefined') {
  HTMLDialogElement.prototype.showModal ??= function showModal(this: HTMLDialogElement) { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close ??= function close(this: HTMLDialogElement) { this.removeAttribute('open'); this.dispatchEvent(new Event('close')); };
}

// The app starts in the browser's language (UI-UX-SPEC H16); tests read the Vietnamese copy, so the test browser is
// Vietnamese.
Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });

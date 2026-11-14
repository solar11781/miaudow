// H14: Google's script is taken off the page when the sign-in page is left (security review of PR #53).
import { describe, expect, it, vi } from 'vitest';
import { GSI_CLIENT, unloadGoogle, type GoogleId } from './google';

describe('unloadGoogle', () => {
  it("cancels Google's sign-in, then removes its script, its stylesheet and its API", () => {
    const cancel = vi.fn(() => {
      expect(document.querySelector(`script[src="${GSI_CLIENT}"]`)).not.toBeNull();
    });
    const id: GoogleId = { initialize: vi.fn(), renderButton: vi.fn(), disableAutoSelect: vi.fn(), cancel };
    window.google = { accounts: { id } };
    const script = document.createElement('script');
    script.src = GSI_CLIENT;
    const css = document.createElement('link');
    css.href = 'https://accounts.google.com/gsi/style';
    document.head.append(script, css);
    unloadGoogle();
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(document.querySelectorAll('script[src^="https://accounts.google.com/gsi/"]').length).toBe(0);
    expect(document.querySelectorAll('link[href^="https://accounts.google.com/gsi/"]').length).toBe(0);
    expect(window.google).toBeUndefined();
  });
});

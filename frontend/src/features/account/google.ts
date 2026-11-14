// Google Identity Services, the ID-token flow of "Sign in with Google" (no access token and no extra scope). The script
// is added to the page only by the sign-in page after the farmer has read the notice (UI-UX-SPEC §12c, H14).
// https://developers.google.com/identity/gsi/web/reference/js-reference

const GSI = 'https://accounts.google.com/gsi/';
export const GSI_CLIENT = `${GSI}client`;

export interface GoogleId {
  initialize(config: { client_id: string; callback: (answer: { credential: string }) => void }): void;
  renderButton(
    parent: HTMLElement,
    options: { type: 'standard'; theme: 'outline'; size: 'large'; text: 'signin_with'; shape: 'pill'; locale: string },
  ): void;
  disableAutoSelect(): void;
  cancel(): void;
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } };
  }
}

let loading: Promise<GoogleId> | null = null;

/** Takes Google's script, its stylesheet and its API off the page when the sign-in page is left, so they are there
 * only on the sign-in pages (H14). */
export function unloadGoogle() {
  loading = null;
  window.google?.accounts.id.cancel(); // closes any prompt or popup Google still has open
  for (const el of document.querySelectorAll(`script[src^="${GSI}"], link[href^="${GSI}"]`)) el.remove();
  delete window.google;
}

/** Adds Google's script once and resolves with its sign-in API; a failed load can be tried again. */
export function loadGoogle(): Promise<GoogleId> {
  loading ??= new Promise<GoogleId>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = GSI_CLIENT;
    script.async = true;
    script.onload = () => {
      const id = window.google?.accounts.id;
      if (id) resolve(id);
      else reject(new Error('Google sign-in did not start'));
    };
    script.onerror = () => reject(new Error('Google sign-in script did not load'));
    document.head.append(script);
  }).catch((err: unknown) => {
    loading = null;
    document.querySelector(`script[src="${GSI_CLIENT}"]`)?.remove();
    throw err;
  });
  return loading;
}

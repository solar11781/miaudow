// Google Identity Services, the ID-token flow of "Sign in with Google" (no access token and no extra scope). The script
// is added to the page only by the sign-in page after the farmer has read the notice (UI-UX-SPEC §12c, H14).
// https://developers.google.com/identity/gsi/web/reference/js-reference

export const GSI_CLIENT = 'https://accounts.google.com/gsi/client';

export interface GoogleId {
  initialize(config: { client_id: string; callback: (answer: { credential: string }) => void }): void;
  renderButton(
    parent: HTMLElement,
    options: { type: 'standard'; theme: 'outline'; size: 'large'; text: 'signin_with'; shape: 'pill'; locale: string },
  ): void;
  disableAutoSelect(): void;
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } };
  }
}

let loading: Promise<GoogleId> | null = null;

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

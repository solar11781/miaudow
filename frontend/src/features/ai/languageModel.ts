import type { Passage } from './knowledge';

/**
 * Integration point for a language model. A model may only rephrase evidence passages it is given; it must not add
 * numbers or claims. It must run on a server: an API key in a Vite bundle is public, so none is ever read here.
 */
export interface ExplanationModel {
  readonly connected: boolean;
  rephrase(question: string, passages: Passage[], lang: 'vi' | 'en'): Promise<string>;
}

/** The default: no model is connected, and the app says so instead of pretending. */
export const notConnected: ExplanationModel = {
  connected: false,
  rephrase: () =>
    Promise.reject(new Error('No language model is connected. Answers come from evidence passages only.')),
};

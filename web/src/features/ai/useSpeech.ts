import { useCallback, useEffect, useRef, useState } from 'react';

// Browser speech only (Web Speech API). Recognition quality for the Nghệ An dialect has not been evaluated, so the
// transcript always goes into the text box for the user to read and correct before anything is sent.

interface Recognition {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  abort(): void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
}
type RecognitionCtor = new () => Recognition;

function recognitionCtor(): RecognitionCtor | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function useSpeech(lang: 'vi' | 'en', onTranscript: (text: string) => void) {
  const Ctor = recognitionCtor();
  const canListen = Ctor !== null;
  const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<Recognition | null>(null);
  const cb = useRef(onTranscript);
  useEffect(() => { cb.current = onTranscript; }, [onTranscript]);

  const listen = useCallback(() => {
    if (!Ctor) return;
    setError(null);
    const r = new Ctor();
    r.lang = lang === 'vi' ? 'vi-VN' : 'en-US';
    r.interimResults = false;
    r.maxAlternatives = 1;
    r.onresult = (e) => {
      const text = e.results[0]?.[0]?.transcript ?? '';
      if (text) cb.current(text);
    };
    r.onerror = (e) => setError(e.error);
    r.onend = () => setListening(false);
    rec.current = r;
    setListening(true);
    r.start();
  }, [Ctor, lang]);

  const stopListening = useCallback(() => { rec.current?.abort(); setListening(false); }, []);

  const speak = useCallback((text: string) => {
    if (!canSpeak) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[•*]/g, ''));
    u.lang = lang === 'vi' ? 'vi-VN' : 'en-US';
    const voice = window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith(lang === 'vi' ? 'vi' : 'en'));
    if (voice) u.voice = voice;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  }, [canSpeak, lang]);

  const stopSpeaking = useCallback(() => { if (canSpeak) window.speechSynthesis.cancel(); setSpeaking(false); }, [canSpeak]);

  useEffect(() => () => { rec.current?.abort(); if (canSpeak) window.speechSynthesis.cancel(); }, [canSpeak]);

  return { canListen, canSpeak, listening, speaking, error, listen, stopListening, speak, stopSpeaking };
}

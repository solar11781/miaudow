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

// Chrome and Edge fill the voice list late; without this wait the "no voice" note would flash on every load.
const VOICE_LOAD_WAIT_MS = 1500;

export function useSpeech(lang: 'vi' | 'en', onTranscript: (text: string) => void) {
  const Ctor = recognitionCtor();
  const canListen = Ctor !== null;
  const hasSynthesis = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>(() =>
    hasSynthesis ? window.speechSynthesis.getVoices() : [],
  );
  const [voicesSettled, setVoicesSettled] = useState(voices.length > 0);
  // Chrome and Edge load voices late and announce it with voiceschanged.
  useEffect(() => {
    if (!hasSynthesis) return;
    const synth = window.speechSynthesis;
    const update = () => {
      setVoices(synth.getVoices());
      setVoicesSettled(true);
    };
    if (synth.getVoices().length > 0) update();
    synth.addEventListener('voiceschanged', update);
    const timer = setTimeout(() => setVoicesSettled(true), VOICE_LOAD_WAIT_MS);
    return () => {
      synth.removeEventListener('voiceschanged', update);
      clearTimeout(timer);
    };
  }, [hasSynthesis]);
  // Never fall back to a voice of another language: it would misread the text.
  const voice = voices.find((v) => new RegExp('^' + lang + '([-_]|$)', 'i').test(v.lang)) ?? null;
  const canSpeak = voice !== null;
  const noVoice = hasSynthesis && voicesSettled && !canSpeak;
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<Recognition | null>(null);
  const cb = useRef(onTranscript);
  useEffect(() => {
    cb.current = onTranscript;
  }, [onTranscript]);

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

  const stopListening = useCallback(() => {
    rec.current?.abort();
    setListening(false);
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (!voice) return;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text.replace(/[•*]/g, ''));
      u.lang = lang === 'vi' ? 'vi-VN' : 'en-US';
      u.voice = voice;
      u.onend = () => setSpeaking(false);
      u.onerror = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(u);
    },
    [voice, lang],
  );

  const stopSpeaking = useCallback(() => {
    if (hasSynthesis) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [hasSynthesis]);

  useEffect(
    () => () => {
      rec.current?.abort();
      if (hasSynthesis) window.speechSynthesis.cancel();
    },
    [hasSynthesis],
  );

  return { canListen, canSpeak, noVoice, listening, speaking, error, listen, stopListening, speak, stopSpeaking };
}

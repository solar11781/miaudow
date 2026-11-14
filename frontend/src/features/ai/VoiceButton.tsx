import { useState } from 'react';
import { Icon } from '../../design-system/Icon';
import { useT } from '../../app/settings';
import s from './assistant.module.css';

/** Voice input starts only after a tap, and only after a note that the browser may send the audio to its speech
 * provider (D-167). */
export function VoiceButton({ listening, listen, stop }: { listening: boolean; listen: () => void; stop: () => void }) {
  const t = useT();
  const [noted, setNoted] = useState(false);
  if (listening) {
    return (
      <button type="button" className={s.mic} aria-pressed="true" onClick={stop}>
        <Icon name="stop" size={20} />{t.copilot.listening}
      </button>
    );
  }
  if (!noted) {
    return (
      <button type="button" className={s.mic} aria-pressed="false" onClick={() => setNoted(true)}>
        <Icon name="mic" size={20} />{t.copilot.speak}
      </button>
    );
  }
  return (
    <span className={s.micNote}>
      <span role="status">{t.copilot.micNote}</span>
      <button type="button" className={s.mic} onClick={listen}>
        <Icon name="mic" size={20} />{t.copilot.micStart}
      </button>
    </span>
  );
}

import { useEffect, useRef, useState } from 'react';
import { Button } from '../../design-system/Button';
import type { IconName } from '../../design-system/Icon';
import s from './account.module.css';

/** A delete button with one inline confirm step: focus moves to the question, and "no" brings it back. */
export function Confirm({
  id,
  label,
  ariaLabel,
  question,
  yes,
  no,
  onYes,
  error,
  leadingIcon,
}: {
  id: string;
  label: string;
  ariaLabel?: string;
  question: string;
  yes: string;
  no: string;
  onYes: () => void;
  error?: string | null;
  leadingIcon?: IconName;
}) {
  const [asking, setAsking] = useState(false);
  const ask = useRef<HTMLParagraphElement>(null);
  const opener = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (asking) ask.current?.focus();
  }, [asking]);

  return (
    <div className="stack">
      <Button
        ref={opener}
        variant="secondary"
        leadingIcon={leadingIcon}
        aria-label={ariaLabel}
        aria-expanded={asking}
        aria-controls={id}
        onClick={() => setAsking(true)}
      >
        {label}
      </Button>
      {asking && (
        <div id={id} className={s.confirm} role="group" aria-labelledby={`${id}-ask`}>
          <p id={`${id}-ask`} ref={ask} tabIndex={-1}>
            <strong>{question}</strong>
          </p>
          <div className="cluster">
            {/* deleting is never the main action of the page, so it does not take the main button style */}
            <Button variant="secondary" leadingIcon="alert" onClick={onYes}>
              {yes}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setAsking(false);
                opener.current?.focus();
              }}
            >
              {no}
            </Button>
          </div>
          {error && <p role="alert">{error}</p>}
        </div>
      )}
    </div>
  );
}

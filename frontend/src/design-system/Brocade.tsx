import s from './Brocade.module.css';

/**
 * A woven band in the spirit of the Thái brocade of western Nghệ An: nested lozenges between rows of small teeth, in
 * turmeric gold, lacquer red and ivory. Drawn for MIAUDOW (not a copy of a specific textile); decoration only.
 */
export function Brocade({ className, ...rest }: { className?: string; 'data-brocade'?: boolean }) {
  return <div className={[s.band, className].filter(Boolean).join(' ')} aria-hidden="true" {...rest} />;
}

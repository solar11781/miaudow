import { useEffect, useMemo, useRef, useState } from 'react';
import { hazards, type RuleCode } from '../../data';
import { cellMagnitude, RULES } from '../../domain/hazards';
import { Icon } from '../../design-system/Icon';
import { useFormat, useSettings, useT } from '../../app/settings';
import { Grid3D } from './Grid3D';
import { createObservatory, hasWebGL, PLACES, WEIGHTED, type Observatory } from './observatoryScene';
import s from './Observatory3D.module.css';

/**
 * The flagship observatory: a WebGL scene of real Nghệ An geometry. Loaded only by the science page (code split),
 * rendered on demand (never a perpetual loop), disposed on unmount; 2D in lite mode, under reduced motion or
 * without WebGL (UI-UX-SPEC H1, D-155).
 */
export function Observatory3D({
  rule,
  year,
  selected,
  onSelect,
}: {
  rule: RuleCode;
  year: number;
  selected: string;
  onSelect: (id: string) => void;
}) {
  const t = useT();
  const f = useFormat();
  const { calm, lang } = useSettings();
  const [want3d, setWant3d] = useState(true);
  const [failed, setFailed] = useState(false);
  const supported = useMemo(() => typeof window !== 'undefined' && hasWebGL(), []);
  const show3d = want3d && !calm && supported && !failed;

  const host = useRef<HTMLDivElement>(null);
  const labels = useRef<HTMLDivElement>(null);
  const stage = useRef<Observatory | null>(null);
  const selectRef = useRef(onSelect);
  useEffect(() => {
    selectRef.current = onSelect;
  }, [onSelect]);

  const magKey = RULES[rule].magnitude;
  const magMax = useMemo(() => Math.max(1, ...Object.values(hazards.magnitudes[magKey]).flat()), [magKey]);

  useEffect(() => {
    const el = host.current;
    const overlay = labels.current;
    if (!show3d || !el || !overlay) return;
    const obs = createObservatory(el, overlay, s.canvas ?? '', (id) => selectRef.current(id));
    if (!obs) {
      queueMicrotask(() => setFailed(true)); // WebGL refused to start: fall back to the 2D map
      return;
    }
    stage.current = obs;
    return () => {
      obs.dispose();
      stage.current = null;
    };
  }, [show3d]);

  const first = useRef(true);
  useEffect(() => {
    stage.current?.setData(rule, year, !first.current);
    first.current = false;
  }, [rule, year, show3d]);
  useEffect(() => {
    stage.current?.setSelected(selected);
  }, [selected, show3d]);

  if (!show3d) {
    return (
      <div className={s.flatWrap}>
        <Grid3D rule={rule} year={year} selected={selected} onSelect={onSelect} forceFlat />
        {!calm && supported && !failed && (
          <button type="button" className={s.switchBack} onClick={() => setWant3d(true)}>
            {t.science.view3d}
          </button>
        )}
        {(failed || !supported) && <p className={s.note}>{t.science.noWebgl}</p>}
      </div>
    );
  }

  const color = RULES[rule].color;
  return (
    <div className={s.wrap}>
      <div
        ref={host}
        className={s.stage}
        tabIndex={0}
        role="group"
        aria-label={`${t.science.mapTitle}. ${t.science.dragHint}`}
        onKeyDown={(e) => {
          const step = { ArrowLeft: [-0.18, 0], ArrowRight: [0.18, 0], ArrowUp: [0, -0.08], ArrowDown: [0, 0.08] }[
            e.key
          ];
          if (!step) return;
          e.preventDefault();
          stage.current?.orbit(step[0] ?? 0, step[1] ?? 0);
        }}
      >
        <div ref={labels} className={s.labels} aria-hidden="true">
          {WEIGHTED.map((c) => (
            <span key={c.id} data-id={c.id} className={[s.value, c.id === selected ? s.valueSel : ''].join(' ')}>
              {f.n(cellMagnitude(magKey, c.id, year))}
            </span>
          ))}
          {PLACES.map((p) => (
            <span key={p.id} data-place={p.id} className={s.place}>
              {lang === 'vi' ? p.vi : p.en}
            </span>
          ))}
        </div>
        <div className={s.controls}>
          <button type="button" onClick={() => stage.current?.orbit(-0.5, 0)} aria-label={t.science.rotateLeft}>
            <Icon name="rotateL" size={20} />
          </button>
          <button type="button" onClick={() => stage.current?.orbit(0.5, 0)} aria-label={t.science.rotateRight}>
            <Icon name="rotateR" size={20} />
          </button>
          <button type="button" onClick={() => stage.current?.reset()} aria-label={t.science.reset}>
            <Icon name="reset" size={20} />
          </button>
          <button type="button" className={s.mode} onClick={() => setWant3d(false)}>
            {t.science.view2d}
          </button>
        </div>
        <p className={s.badge}>
          <span className={s.dot} aria-hidden="true" />
          {t.science.realGeometryShort}
        </p>
        <p className={s.hint}>{t.science.dragHint}</p>
      </div>
      <div className={s.legend}>
        <span>
          <i style={{ background: color }} />
          {t.science.met}
        </span>
        <span>
          <i style={{ background: `color-mix(in srgb, ${color} 28%, #3c5a43)` }} />
          {t.science.notMet}
        </span>
        <span>
          <i className={s.dash} />
          {t.science.cellFootprint}
        </span>
        <span>{t.science.realGeometry}</span>
        <span className="mono">
          {t.science.heightIs}: {RULES[rule].unit[lang]} · max {f.n(magMax)}
        </span>
      </div>
    </div>
  );
}

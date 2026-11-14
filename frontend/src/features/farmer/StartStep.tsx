import { useFarmer } from './FarmerLayout';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { Media } from '../../design-system/Media';
import { usePick, useT } from '../../app/settings';
import { media } from '../../data/media';
import s from './farmer.module.css';

export function StartStep() {
  const t = useT();
  const pick = usePick();
  const { search } = useFarmer();
  return (
    <div className={s.shell}>
      <article className={`${s.startCard} surface-forest`}>
        <div className={s.startPhoto}>
          <Media slug="do-luong-nam-son-road-rice" priority sizes="(min-width: 640px) 560px, 100vw" />
          <span className={s.photoCaption}>{pick(media('do-luong-nam-son-road-rice').caption)}</span>
        </div>
        <div className={s.startBody}>
          <p className="eyebrow">{t.farmer.startEyebrow}</p>
          <h1 className={`display ${s.startTitle}`}>{t.farmer.startTitle}</h1>
          <p className={s.startLead}>{t.farmer.startLead}</p>
          <ol className={s.startList}>
            {t.home.steps.map((st, i) => (
              <li key={st.title}><span className={s.startNum}>{i + 1}</span>{st.title}</li>
            ))}
          </ol>
          <ButtonLink to={{ pathname: '/nong-dan/ruong', search }} size="lg" block icon="arrowRight">{t.farmer.startCta}</ButtonLink>
        </div>
      </article>
      <p className={s.support}><Icon name="user" size={20} />{t.common.support}</p>
    </div>
  );
}

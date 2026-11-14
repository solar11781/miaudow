import { Link } from 'react-router-dom';
import { useT } from '../app/settings';
import { Icon } from './Icon';
import s from './CoreTag.module.css';

export type Core = 'climate' | 'evidence' | 'crop' | 'copilot';

/** Names the AI core at work in a section and links to where the four cores are explained (home page). */
export function CoreTag({ core }: { core: Core }) {
  const t = useT();
  return (
    <Link to="/" state={{ to: 'cores' }} className={s.tag} data-core={core} viewTransition>
      <Icon name="spark" size={16} />{t.common.coreTag[core]}
    </Link>
  );
}

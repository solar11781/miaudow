import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router-dom';
import { useLocalTo } from '../app/paths';
import { Icon, type IconName } from './Icon';
import s from './Button.module.css';

type Variant = 'primary' | 'secondary' | 'ghost' | 'quiet';
type Size = 'md' | 'lg';

interface Common {
  variant?: Variant;
  size?: Size;
  /** Trailing icon; it moves a little on hover, the button itself stays still. */
  icon?: IconName;
  leadingIcon?: IconName;
  block?: boolean;
  children: ReactNode;
}

const cls = (v: Variant, z: Size, block?: boolean, extra?: string) =>
  [s.btn, s[v], s[z], block ? s.block : '', extra ?? ''].filter(Boolean).join(' ');

function Inner({ icon, leadingIcon, children }: Pick<Common, 'icon' | 'leadingIcon' | 'children'>) {
  return (
    <>
      {leadingIcon && <Icon name={leadingIcon} size={18} />}
      <span className={s.label}>{children}</span>
      {icon && (
        <span className={s.icon}>
          <Icon name={icon} size={18} strokeWidth={2} />
        </span>
      )}
    </>
  );
}

export const Button = forwardRef<HTMLButtonElement, Common & ButtonHTMLAttributes<HTMLButtonElement>>(function Button(
  { variant = 'primary', size = 'md', icon, leadingIcon, block, children, className, type = 'button', ...rest },
  ref,
) {
  return (
    <button ref={ref} type={type} className={cls(variant, size, block, className)} {...rest}>
      <Inner icon={icon} leadingIcon={leadingIcon}>
        {children}
      </Inner>
    </button>
  );
});

export function ButtonLink({
  variant = 'primary',
  size = 'md',
  icon,
  leadingIcon,
  block,
  children,
  className,
  to,
  ...rest
}: Common & LinkProps) {
  const local = useLocalTo();
  return (
    <Link className={cls(variant, size, block, className)} to={local(to)} {...rest}>
      <Inner icon={icon} leadingIcon={leadingIcon}>
        {children}
      </Inner>
    </Link>
  );
}

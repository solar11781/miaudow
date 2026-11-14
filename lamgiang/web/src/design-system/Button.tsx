import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router-dom';
import { Icon, type IconName } from './Icon';
import s from './Button.module.css';

type Variant = 'primary' | 'secondary' | 'ghost' | 'quiet';
type Size = 'md' | 'lg';

interface Common {
  variant?: Variant;
  size?: Size;
  /** Trailing icon; the primary button shows it in a dark disc, like a seal pressed into the pill. */
  icon?: IconName;
  leadingIcon?: IconName;
  block?: boolean;
  children: ReactNode;
}

const cls = (v: Variant, z: Size, block?: boolean, extra?: string) =>
  [s.btn, s[v], s[z], block ? s.block : '', extra ?? ''].filter(Boolean).join(' ');

function Inner({ icon, leadingIcon, children, variant }: Pick<Common, 'icon' | 'leadingIcon' | 'children' | 'variant'>) {
  return (
    <>
      {leadingIcon && <Icon name={leadingIcon} size={18} />}
      <span className={s.label}>{children}</span>
      {icon && (variant === 'primary' ? <span className={s.disc}><Icon name={icon} size={18} strokeWidth={2} /></span> : <Icon name={icon} size={18} />)}
    </>
  );
}

export const Button = forwardRef<HTMLButtonElement, Common & ButtonHTMLAttributes<HTMLButtonElement>>(function Button(
  { variant = 'primary', size = 'md', icon, leadingIcon, block, children, className, type = 'button', ...rest },
  ref,
) {
  return (
    <button ref={ref} type={type} className={cls(variant, size, block, className)} {...rest}>
      <Inner icon={icon} leadingIcon={leadingIcon} variant={variant}>{children}</Inner>
    </button>
  );
});

export function ButtonLink({ variant = 'primary', size = 'md', icon, leadingIcon, block, children, className, ...rest }: Common & LinkProps) {
  return (
    <Link className={cls(variant, size, block, className)} viewTransition {...rest}>
      <Inner icon={icon} leadingIcon={leadingIcon} variant={variant}>{children}</Inner>
    </Link>
  );
}

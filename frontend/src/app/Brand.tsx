// The Miaudow logo (designed by member B, assets/brand/miaudow-logo-sheet.png; files built by
// web/pipeline/build_brand.mjs): the rounded app icon, the emblem and the light wordmark.

/** The app icon: rice ear, terraces, river and satellite on deep green. */
export function BrandMark({ size = 36 }: { size?: number }) {
  return (
    <img
      src="brand/icon-96.png"
      width={size}
      height={size}
      alt=""
      aria-hidden="true"
      style={{ borderRadius: size * 0.22, flex: 'none' }}
    />
  );
}

/** The emblem on a transparent background, for large places (footer, copilot). */
export function BrandEmblem({ width = 180, className }: { width?: number; className?: string }) {
  return (
    <picture className={className}>
      <source type="image/webp" srcSet="brand/emblem-360.webp 360w, brand/emblem-720.webp 720w" sizes={`${width}px`} />
      <img
        src="brand/emblem-360.webp"
        width={width}
        height={Math.round(width * 0.79)}
        alt=""
        aria-hidden="true"
        style={{ display: 'block', width, height: 'auto' }}
      />
    </picture>
  );
}

/** The wordmark MIAUDOW in ivory with its orange accent; `label` is the accessible name. */
export function BrandWordmark({
  height = 22,
  label = 'Miaudow',
  className,
}: {
  height?: number;
  label?: string;
  className?: string;
}) {
  return (
    <img
      className={className}
      src="brand/wordmark-light-360.webp"
      srcSet="brand/wordmark-light-360.webp 1x, brand/wordmark-light-720.webp 2x"
      height={height}
      width={Math.round(height * 6)}
      alt={label}
      style={{ display: 'block', height, width: 'auto' }}
    />
  );
}

/** The short names of the datasets a response cites, in the order of `names`, each name once. `names` lists only
 * datasets we use, so an id cited as considered and not used (e.g. ERA5 on the method page) is never named. */
export function dataNames(sources: Record<string, unknown>, names: Record<string, string>): string[] {
  return [
    ...new Set(
      Object.entries(names)
        .filter(([id]) => id in sources)
        .map(([, name]) => name),
    ),
  ];
}

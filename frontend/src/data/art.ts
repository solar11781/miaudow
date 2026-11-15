// Art direction: which picture plays which part. Only licensed photographs and the AI illustrations (D-167).

/** A picture for wide screens and, optionally, a taller one for phones. */
export interface Shot {
  slug: string;
  narrow?: string;
}

interface ArtDirection {
  hero: Shot[];
  problem: Shot;
  cores: [Shot, Shot, Shot, Shot];
  climate: Shot;
  verse: Shot;
  steps: [Shot, Shot, Shot, Shot];
  observatory: Shot;
  invite: Shot;
  farmerStart: Shot;
  officer: Shot;
  pageHead: { science: Shot; evidence: Shot; assistant: Shot };
}

export const ART: ArtDirection = {
  hero: [
    { slug: 'nam-dan-ql46-rice-plain' },
    { slug: 'do-luong-nam-son-road-rice' },
    { slug: 'lam-river-hong-linh-view' },
  ],
  problem: { slug: 'con-cuong-chau-khe-rice-field' },
  cores: [{ slug: 'c1-horizon' }, { slug: 'a3-rice' }, { slug: 'd2-fields' }, { slug: 'b4-river' }],
  climate: { slug: 'lam-river-vinh-ben-thuy' },
  verse: { slug: 'thanh-chuong-tea-hills' },
  steps: [{ slug: 'c2-fields' }, { slug: 'b1-horizon' }, { slug: 'a3-rice' }, { slug: 'd2-fields' }],
  observatory: { slug: 'lam-river-vinh-ben-thuy' },
  invite: { slug: 'd1-horizon' },
  farmerStart: { slug: 'do-luong-nam-son-road-rice' },
  officer: { slug: 'do-luong-lam-son-communal-house' },
  pageHead: {
    science: { slug: 'thanh-chuong-tea-hills' },
    evidence: { slug: 'con-cuong-binh-chuan-water-wheels' },
    assistant: { slug: 'con-cuong-lam-river-chau-khe' },
  },
};

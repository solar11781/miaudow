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
  pageHead: { science: Shot; evidence: Shot; assistant: Shot; method: Shot };
}

export const ART: ArtDirection = {
  hero: [
    { slug: 'terrace-sunset-reflection', narrow: 'ninh-hai-sunset' },
    { slug: 'hoang-su-phi-nam-khoa-terraces', narrow: 'ninh-hai-karst-fields' },
    { slug: 'mai-chau-buffalo-ploughing' },
  ],
  problem: { slug: 'paddy-farmer-seedlings' },
  cores: [
    { slug: 'ha-giang-golden-terraces-clouds' },
    { slug: 'long-xuyen-ripe-rice' },
    { slug: 'terraced-rice-fields' },
    { slug: 'farmer-carrying-seedlings' },
  ],
  climate: { slug: 'son-la-terraced-paddies' },
  verse: { slug: 'pu-luong-terraces' },
  steps: [
    { slug: 'paddy-field-workers' },
    { slug: 'ha-giang-tea-plantation' },
    { slug: 'eggplant-farm-south' },
    { slug: 'riverbank-afternoon' },
  ],
  observatory: { slug: 'ninh-binh-karst-fields' },
  invite: { slug: 'sa-pa-patterns-from-the-sky' },
  farmerStart: { slug: 'planting-rice' },
  officer: { slug: 'mai-chau-houses-rice' },
  pageHead: {
    science: { slug: 'sa-pa-rice-paddies' },
    evidence: { slug: 'trang-an-river' },
    assistant: { slug: 'ha-giang-terraces-village' },
    method: { slug: 'terraced-rice-fields' },
  },
};

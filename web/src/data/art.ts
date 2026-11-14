// Art direction: which picture plays which part. With the team's mood photographs built on this machine
// (pipeline/build_mood.mjs) the pages use them; without them (any published build) the licensed photographs and the
// concept illustrations take the same parts, so nothing breaks and nothing unlicensed ships.
import { HAS_MOOD } from './media';

/** A picture for wide screens and, optionally, a taller one for phones. */
export interface Shot { slug: string; narrow?: string }

interface ArtDirection {
  hero: Shot[];
  problem: Shot;
  cores: [Shot, Shot, Shot, Shot];
  climate: Shot;
  steps: [Shot, Shot, Shot, Shot];
  observatory: Shot;
  invite: Shot;
  farmerStart: Shot;
  officer: Shot;
  pageHead: { science: Shot; evidence: Shot; assistant: Shot };
}

const MOOD: ArtDirection = {
  hero: [
    { slug: 'mood-threshing', narrow: 'mood-river-terraces' },
    { slug: 'mood-karst-river-sunset', narrow: 'mood-seedlings' },
    { slug: 'mood-valley-village', narrow: 'mood-winnowing' },
  ],
  problem: { slug: 'mood-seedlings' },
  cores: [
    { slug: 'mood-terraces-sunbeams' },
    { slug: 'mood-grain-jars' },
    { slug: 'mood-terraces-road' },
    { slug: 'mood-buffalo-child' },
  ],
  climate: { slug: 'mood-river-terraces' },
  steps: [
    { slug: 'mood-field-ditch-workers' },
    { slug: 'mood-tea-hills-mist' },
    { slug: 'mood-lotus-hat' },
    { slug: 'mood-winnowing' },
  ],
  observatory: { slug: 'mood-karst-valley' },
  invite: { slug: 'mood-green-field-aerial' },
  farmerStart: { slug: 'mood-seedling-bundle' },
  officer: { slug: 'mood-village-tree' },
  pageHead: {
    science: { slug: 'mood-flower-hill-pickers' },
    evidence: { slug: 'mood-karst-valley' },
    assistant: { slug: 'mood-valley-village' },
  },
};

const LICENSED: ArtDirection = {
  hero: [
    { slug: 'nam-dan-ql46-rice-plain' },
    { slug: 'do-luong-nam-son-road-rice' },
    { slug: 'lam-river-hong-linh-view' },
  ],
  problem: { slug: 'con-cuong-chau-khe-rice-field' },
  cores: [{ slug: 'c1-horizon' }, { slug: 'a3-rice' }, { slug: 'd2-fields' }, { slug: 'b4-river' }],
  climate: { slug: 'lam-river-vinh-ben-thuy' },
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

export const ART: ArtDirection = HAS_MOOD ? MOOD : LICENSED;

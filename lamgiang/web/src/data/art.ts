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
  verse: Shot;
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
    { slug: 'mood-river-terraces' },
    { slug: 'mood-buffalo-child' },
  ],
  climate: { slug: 'mood-river-terraces' },
  verse: { slug: 'mood-terraces-road' },
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
  },
};

export const ART: ArtDirection = HAS_MOOD ? MOOD : LICENSED;

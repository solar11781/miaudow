// The governed plan text: risk lines, "why" lines and limitations come only from api/rules/rotations.yaml
// (scripts/sync_rotations.py → data/canonical/rotations.generated.json); applicability and the questions for the
// extension officer come from the API's decision core (data/canonical/decision.json). The web app never writes its own.
import rotationsJson from '@data/rotations.generated.json';
import decisionJson from '@data/decision.json';
import type { Bilingual } from '../domain/provenance';
import type { PlanId } from '../domain/plans';

export interface RiskLine {
  text: Bilingual;
  source_id: string;
  location: string;
  location_precision?: string;
  quote: string;
}
interface RulebookPlan {
  id: string;
  why: { why: Bilingual; evidence: Bilingual; benefits: Bilingual; gaps: Bilingual } | null;
  risk_lines: RiskLine[];
  limitations: Bilingual[];
}
interface DecisionPlan {
  applicability: Record<string, Bilingual>;
  questions_for_officer: Bilingual[];
}

const ROTATIONS = rotationsJson as unknown as { plans: RulebookPlan[] };
const DECISION = decisionJson as unknown as { plans: Record<string, DecisionPlan>; missing_information: Bilingual[] };

/** The farmer page's plan ids next to the rulebook's ids. */
export const RULEBOOK_ID: Record<PlanId, string> = {
  cc5: 'usual',
  p03: 'usual_p03',
  cc1: 'cc1',
  cc2: 'cc2',
  cc3: 'cc3',
  cc4: 'cc4',
};

export function rulebookPlan(id: PlanId): RulebookPlan | undefined {
  return ROTATIONS.plans.find((p) => p.id === RULEBOOK_ID[id]);
}

export function decisionPlan(id: PlanId): DecisionPlan | undefined {
  return DECISION.plans[RULEBOOK_ID[id]];
}

export const MISSING_INFORMATION = DECISION.missing_information;

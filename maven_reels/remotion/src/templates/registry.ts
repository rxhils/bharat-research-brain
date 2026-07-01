// Remotion-side template registry (mirrors step_template_selector.py).
//
// Maven reels share ONE proven composition (MavenReel.tsx) parameterized by
// `scenes` + `theme.accent` + `variation`. A "template" is a named scene
// structure the Python Template Selector emits; MavenReel renders whichever
// scene list it is given. This keeps the render path single, tested, and safe
// while still giving five distinct story formats.
export type TemplateId =
  | "market_move_explainer"
  | "sector_breakdown"
  | "policy_impact"
  | "company_shock"
  | "what_investors_missed";

export const TEMPLATES: Record<TemplateId, { label: string; sceneStructure: string[] }> = {
  market_move_explainer: {
    label: "Market Move Explainer",
    sceneStructure: ["hook", "index_card", "sector_chips", "reason_card", "mini_chart", "takeaway", "cta"],
  },
  sector_breakdown: {
    label: "Sector Breakdown",
    sceneStructure: ["hook", "sector_card", "sector_chips", "what_moved", "why_moved", "takeaway", "cta"],
  },
  policy_impact: {
    label: "Policy Impact",
    sceneStructure: ["hook", "policy_card", "affected_sectors", "what_changes", "why_matters", "cta"],
  },
  company_shock: {
    label: "Company Shock",
    sceneStructure: ["hook", "company_card", "what_happened", "market_reaction", "why_matters", "cta"],
  },
  what_investors_missed: {
    label: "What Investors Missed",
    sceneStructure: ["hook", "misconception", "hidden_reason", "simple_explanation", "takeaway", "cta"],
  },
};

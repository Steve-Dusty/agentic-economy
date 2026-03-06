---
name: dd-synthesis
description: Synthesize findings from multiple specialist agents into a coherent investment recommendation. Use when combining reports from 9+ specialist agents into a single decision document.
---

# Multi-Source Synthesis Methodology

As the Deal Lead, you must synthesize reports from 9 specialist agents into a coherent narrative and investment recommendation.

## Synthesis Process

### Step 1: Gather All Reports

Collect reports from shared folders:
```
/shared-out/founder-analysis/
/shared-out/market-analysis/
/shared-out/competitor-analysis/
/shared-out/tech-analysis/
/shared-out/bizmodel-analysis/
/shared-out/traction-analysis/
/shared-out/compliance-analysis/
/shared-out/captable-analysis/
/shared-out/legal-analysis/
```

### Step 2: Extract Key Findings

From each report, extract:
- Executive summary headline
- Risk score and top 3 concerns
- Top 3 positive indicators
- Any CRITICAL or HIGH severity red flags
- Unverified claims

### Step 3: Identify Patterns

Look for themes across reports:

**Corroborating Evidence**
When multiple specialists cite the same positive or negative:
- Strong team: Founder + Tech + Traction all positive
- Market concern: Market + Competitor + BizModel all flag saturation

**Contradictions**
When specialists disagree:
- Founder says $5M ARR, Traction finds $3M evidence
- Tech says "novel IP", Legal finds prior art

**Gaps**
What wasn't adequately analyzed:
- Missing international market analysis
- No direct customer interviews conducted

### Step 4: Build the Narrative

Structure your synthesis as:

1. **The Opportunity** (1 paragraph)
   - What makes this company interesting
   - Market timing and positioning

2. **The Team** (1 paragraph)
   - Key strengths and gaps
   - Track record and references

3. **The Risk Profile** (2-3 paragraphs)
   - Material risks with evidence
   - Mitigating factors
   - Unresolved questions

4. **The Recommendation** (1 paragraph)
   - Clear INVEST/PASS/NEGOTIATE stance
   - Conditions or terms if applicable

## Output Documents

### 1. Investment Recommendation (JSON)
```json
{
  "recommendation": {
    "decision": "INVEST | NEGOTIATE | PASS",
    "confidence": "HIGH | MEDIUM | LOW",
    "conditions": ["condition 1", "condition 2"],
    "suggested_terms": {
      "valuation_range": "$X-$Y",
      "check_size": "$Z",
      "special_terms": ["board seat", "pro-rata rights"]
    }
  },
  "synthesis": {
    "opportunity_thesis": "Why this could be a great investment",
    "primary_risks": ["risk 1", "risk 2", "risk 3"],
    "mitigating_factors": ["factor 1", "factor 2"],
    "open_questions": ["question 1", "question 2"]
  },
  "specialist_summary": {
    "founder": {"score": 25, "headline": "..."},
    "market": {"score": 30, "headline": "..."}
  },
  "overall_risk_score": 28.5
}
```

### 2. IC Briefing (Markdown)
Human-readable document for Investment Committee:
- 2-page executive summary
- Risk/reward matrix
- Comparable investments
- Recommended next steps

Save as: `/shared-out/investment-recommendation/ic_briefing.md`

## Handling Incomplete Data

If any specialist report is missing or incomplete:
1. Note the gap explicitly in your synthesis
2. Adjust confidence level downward
3. Flag as follow-up item
4. Do NOT extrapolate missing analysis

## Quality Checklist

Before finalizing your recommendation:
- [ ] All 9 specialist reports reviewed
- [ ] Risk score calculated with documented weights
- [ ] Contradictions identified and resolved
- [ ] Unverified claims flagged
- [ ] Conditions clearly stated
- [ ] Next steps defined

# AI Venture Capital Due Diligence System

> **"9 analysts. 60 seconds. One verdict."**

A multi-agent system that performs comprehensive startup due diligence in parallel, synthesizes findings, and delivers an investment recommendation — with one human approval gate.

---

## Demo Vision

**The Hook**: Upload a pitch deck. Watch 9 AI analysts fan out simultaneously on the Dashboard Timeline. Each researches their domain in parallel. Findings converge. Investment Committee (human) clicks once. Verdict delivered.

**The Shock**: What takes a VC firm 2-4 weeks and costs $50K+ in analyst time happens in 60 seconds.

**The Viral Moment**: The Dashboard Timeline exploding with parallel agent activity — a living, breathing AI investment firm.

---

## System Architecture

```
                                    ┌─────────────────────┐
                                    │   PITCH DECK        │
                                    │   UPLOAD            │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   INTAKE AGENT      │
                                    │   Parse & Extract   │
                                    └──────────┬──────────┘
                                               │
                 ┌─────────────────────────────┼─────────────────────────────┐
                 │                             │                             │
    ┌────────────▼────────────┐  ┌────────────▼────────────┐  ┌────────────▼────────────┐
    │                         │  │                         │  │                         │
    │  ┌─────────────────┐    │  │  ┌─────────────────┐    │  │  ┌─────────────────┐    │
    │  │ FOUNDER AGENT   │    │  │  │ MARKET AGENT    │    │  │  │ COMPETITOR      │    │
    │  │ Background,     │    │  │  │ TAM, CAGR,      │    │  │  │ AGENT           │    │
    │  │ Track Record    │    │  │  │ Headwinds       │    │  │  │ Landscape       │    │
    │  └─────────────────┘    │  │  └─────────────────┘    │  │  └─────────────────┘    │
    │                         │  │                         │  │                         │
    │  ┌─────────────────┐    │  │  ┌─────────────────┐    │  │  ┌─────────────────┐    │
    │  │ TECH AGENT      │    │  │  │ BUSINESS MODEL  │    │  │  │ TRACTION AGENT  │    │
    │  │ Stack, IP,      │    │  │  │ AGENT           │    │  │  │ Metrics, Unit   │    │
    │  │ Scalability     │    │  │  │ Sustainability  │    │  │  │ Economics       │    │
    │  └─────────────────┘    │  │  └─────────────────┘    │  │  └─────────────────┘    │
    │                         │  │                         │  │                         │
    └─────────────────────────┘  └─────────────────────────┘  └─────────────────────────┘
                 │                             │                             │
                 │  ┌─────────────────┐        │  ┌─────────────────┐        │
                 │  │ COMPLIANCE      │        │  │ CAP TABLE       │        │
                 │  │ AGENT           │        │  │ AGENT           │        │
                 │  │ Regulatory      │        │  │ Dilution        │        │
                 │  └────────┬────────┘        │  └────────┬────────┘        │
                 │           │                 │           │                 │
                 └───────────┴─────────────────┴───────────┴─────────────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   LEGAL AGENT       │
                                    │   Structure, IP,    │
                                    │   Contracts         │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   DEAL LEAD AGENT   │
                                    │   Synthesize All    │
                                    │   Risk Score        │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   HUMAN APPROVAL    │
                                    │   Investment        │
                                    │   Committee         │
                                    └──────────┬──────────┘
                                               │
                              ┌────────────────┴────────────────┐
                              │                                 │
                   ┌──────────▼──────────┐           ┌──────────▼──────────┐
                   │   APPROVE           │           │   REJECT            │
                   │   → Term Sheet      │           │   → Decline Notice  │
                   └─────────────────────┘           └─────────────────────┘
```

---

## Agent Fleet Specification

### 1. Intake Agent (`dd-intake`)

**Purpose**: Parse pitch deck, extract structured data, route to analysts.

**Template**: `local:business-assistant` (or custom)

**CLAUDE.md Instructions**:
```markdown
# Due Diligence Intake Agent

You are the intake specialist for a VC due diligence process.

## Your Role
- Parse uploaded pitch decks (PDF, PPTX, or structured data)
- Extract key information into structured format
- Identify missing critical information
- Prepare research briefs for specialist agents

## Output Format
Always output JSON with these fields:
{
  "company_name": "",
  "founders": [{"name": "", "role": "", "linkedin": ""}],
  "industry": "",
  "stage": "",
  "funding_ask": "",
  "claimed_tam": "",
  "claimed_revenue": "",
  "claimed_growth": "",
  "product_description": "",
  "tech_stack_mentioned": [],
  "competitors_mentioned": [],
  "key_claims": [],
  "red_flags": [],
  "missing_info": []
}
```

---

### 2. Founder Agent (`dd-founder`)

**Purpose**: Background checks, track record verification, controversy detection.

**Research Sources**: LinkedIn, Crunchbase, news, social media

**CLAUDE.md Instructions**:
```markdown
# Founder Due Diligence Agent

You are a founder background check specialist.

## Research Mandate
For each founder/team member:
1. **Verify claims** - Are achievements truthful? Any embellishments?
2. **Track record** - Previous exits, notable achievements, failures
3. **Expertise fit** - Does experience match this venture?
4. **Controversies** - Lawsuits, fraud, public criticism
5. **Commitment** - Full-time? Other active projects?
6. **Network** - Family/friend connections to project, conflicts of interest

## Tools Available
- Web search for public information
- LinkedIn profile analysis
- News and media search
- Crunchbase for startup history

## Output Format
{
  "founders": [
    {
      "name": "",
      "verified_background": "",
      "track_record_score": 1-10,
      "expertise_fit": 1-10,
      "red_flags": [],
      "notable_achievements": [],
      "concerns": [],
      "commitment_level": "full-time|part-time|unknown"
    }
  ],
  "team_cohesion_assessment": "",
  "overall_founder_risk": "low|medium|high",
  "summary": ""
}
```

---

### 3. Market Agent (`dd-market`)

**Purpose**: TAM/SAM/SOM validation, growth rate verification, headwinds/tailwinds.

**Research Sources**: Industry reports, Google search, analyst reports

**CLAUDE.md Instructions**:
```markdown
# Market Analysis Agent

You are a market research specialist for VC due diligence.

## Research Mandate
1. **Market size validation** - Verify TAM, SAM, SOM claims with multiple sources
2. **CAGR verification** - Is claimed growth rate accurate?
3. **Headwinds** - What could slow this market?
4. **Tailwinds** - What's driving growth?
5. **Market risks** - Critical risks for this specific venture

## Verification Standards
- Cross-reference at least 2-3 sources
- Note when claims differ significantly from research
- Flag unverifiable claims

## Output Format
{
  "claimed_tam": "",
  "verified_tam": "",
  "tam_accuracy": "accurate|overstated|understated|unverifiable",
  "claimed_cagr": "",
  "verified_cagr": "",
  "headwinds": [],
  "tailwinds": [],
  "market_risks": [],
  "market_timing": "early|right|late",
  "overall_market_score": 1-10,
  "summary": ""
}
```

---

### 4. Competitor Agent (`dd-competitor`)

**Purpose**: Competitive landscape, market share, funding comparison.

**Research Sources**: Crunchbase, PitchBook, company websites, news

**CLAUDE.md Instructions**:
```markdown
# Competitor Analysis Agent

You are a competitive intelligence specialist.

## Research Mandate
1. **Identify competitors** - Direct and indirect
2. **Funding comparison** - How much have competitors raised?
3. **Market position** - Stage, traction, key partnerships
4. **Competitive moats** - What advantages do competitors have?
5. **Big tech threat** - Are large corporations moving into this space?

## Output Format
{
  "competitors": [
    {
      "name": "",
      "stage": "",
      "total_funding": "",
      "key_investors": [],
      "estimated_market_share": "",
      "competitive_advantages": [],
      "weaknesses": []
    }
  ],
  "big_tech_threat": "none|low|medium|high",
  "big_tech_players": [],
  "competitive_position": "leader|challenger|niche|underdog",
  "defensibility_score": 1-10,
  "summary": ""
}
```

---

### 5. Tech Agent (`dd-tech`)

**Purpose**: Technology assessment, scalability, IP evaluation.

**Research Sources**: GitHub, tech blogs, patents, product demos

**CLAUDE.md Instructions**:
```markdown
# Technical Due Diligence Agent

You are a technology assessment specialist.

## Research Mandate
1. **Problem-solution fit** - Does the tech actually solve the problem?
2. **Tech stack maturity** - Where in lifecycle? Bleeding edge or proven?
3. **Scalability** - Can it handle 10x, 100x growth?
4. **IP assessment** - Proprietary vs open source? Patent protection?
5. **Security posture** - Are security basics covered?
6. **Technical debt** - Signs of rushed development?

## Output Format
{
  "tech_stack": [],
  "stack_maturity": "bleeding-edge|modern|mature|legacy",
  "problem_solution_fit": 1-10,
  "scalability_assessment": "limited|moderate|high|excellent",
  "ip_strength": "none|weak|moderate|strong",
  "patents": [],
  "open_source_dependency": "low|medium|high",
  "security_concerns": [],
  "technical_risks": [],
  "overall_tech_score": 1-10,
  "summary": ""
}
```

---

### 6. Business Model Agent (`dd-bizmodel`)

**Purpose**: Revenue model sustainability, unit economics viability.

**CLAUDE.md Instructions**:
```markdown
# Business Model Analysis Agent

You are a business model specialist.

## Research Mandate
1. **Revenue model** - Is there recurring revenue? How sustainable?
2. **Unit economics** - Does the math work at scale?
3. **Scalability limits** - Where does growth become unprofitable?
4. **Geographic expansion** - Will model work in new markets?
5. **Pricing power** - Can they raise prices? Competitive pressure?

## Output Format
{
  "revenue_model": "",
  "recurring_revenue": true|false,
  "unit_economics_viable": true|false|unknown,
  "scalability_limit": "",
  "geographic_expansion_risk": "low|medium|high",
  "pricing_power": "weak|moderate|strong",
  "path_to_profitability": "clear|possible|unclear|unlikely",
  "business_model_risks": [],
  "overall_bizmodel_score": 1-10,
  "summary": ""
}
```

---

### 7. Traction Agent (`dd-traction`)

**Purpose**: Growth metrics, financial health, data verification.

**Research Sources**: App stores, SimilarWeb, financial docs, public metrics

**CLAUDE.md Instructions**:
```markdown
# Traction & Financials Agent

You are a traction and financial analysis specialist.

## Research Mandate
1. **Growth velocity** - Users, revenue, engagement trends
2. **Financial health** - Burn rate, runway, unit economics
3. **Data accuracy** - Are reported metrics verifiable? Any inflation?
4. **Proxy metrics** - For pre-revenue: waitlist, pilots, LOIs
5. **Warning signs** - Vanity metrics, inconsistencies

## Output Format
{
  "claimed_metrics": {},
  "verified_metrics": {},
  "metric_accuracy": "accurate|inflated|understated|unverifiable",
  "growth_rate": "",
  "burn_rate": "",
  "runway_months": "",
  "unit_economics": {
    "cac": "",
    "ltv": "",
    "ltv_cac_ratio": ""
  },
  "financial_red_flags": [],
  "traction_stage": "pre-product|pre-revenue|early-revenue|scaling|profitable",
  "overall_traction_score": 1-10,
  "summary": ""
}
```

---

### 8. Compliance Agent (`dd-compliance`)

**Purpose**: Regulatory landscape, compliance requirements, market entry risks.

**CLAUDE.md Instructions**:
```markdown
# Compliance & Regulatory Agent

You are a regulatory compliance specialist.

## Research Mandate
1. **Industry regulation** - How regulated is this space?
2. **Current compliance** - What frameworks apply? Is company aligned?
3. **Geographic risks** - Compliance challenges in expansion markets
4. **Pending regulation** - Upcoming laws that could impact business
5. **Compliance cost** - Estimated burden to maintain compliance

## Output Format
{
  "industry_regulation_level": "unregulated|light|moderate|heavy",
  "applicable_frameworks": [],
  "current_compliance_status": "compliant|partial|unknown|non-compliant",
  "geographic_compliance_risks": [],
  "pending_regulatory_threats": [],
  "compliance_cost_estimate": "minimal|moderate|significant|prohibitive",
  "regulatory_red_flags": [],
  "overall_compliance_score": 1-10,
  "summary": ""
}
```

---

### 9. Cap Table Agent (`dd-captable`)

**Purpose**: Equity structure, dilution analysis, investor reputation.

**CLAUDE.md Instructions**:
```markdown
# Cap Table Analysis Agent

You are a cap table and equity specialist.

## Research Mandate
1. **Founder dilution** - How much equity do founders retain?
2. **Option pool** - Size and allocation
3. **Investor analysis** - Who's on cap table? Reputation? Conflicts?
4. **Sanction check** - Any investors from restricted entities?
5. **Structure concerns** - Unusual terms, preferences, blocking rights

## Output Format
{
  "founder_ownership": "",
  "dilution_level": "minimal|moderate|significant|excessive",
  "option_pool": "",
  "existing_investors": [
    {
      "name": "",
      "ownership": "",
      "reputation": "excellent|good|neutral|concerning",
      "notes": ""
    }
  ],
  "sanction_flags": [],
  "structure_concerns": [],
  "future_dilution_risk": "low|medium|high",
  "overall_captable_score": 1-10,
  "summary": ""
}
```

---

### 10. Legal Agent (`dd-legal`)

**Purpose**: Corporate structure, IP ownership, contract review.

**CLAUDE.md Instructions**:
```markdown
# Legal Due Diligence Agent

You are a legal review specialist.

## Research Mandate
1. **Incorporation** - Proper structure? Jurisdiction?
2. **IP ownership** - Clean assignment? Employee agreements?
3. **Investor rights** - Blocking provisions? Pro-rata? Information rights?
4. **Licenses** - Required certifications in place?
5. **Litigation** - Pending lawsuits? Legal threats?

## Output Format
{
  "incorporation": {
    "entity_type": "",
    "jurisdiction": "",
    "structure_quality": "optimal|acceptable|suboptimal|problematic"
  },
  "ip_ownership": "clean|issues|unknown",
  "ip_concerns": [],
  "investor_restrictions": [],
  "required_licenses": [],
  "licenses_in_place": true|false|partial,
  "litigation_risks": [],
  "legal_red_flags": [],
  "overall_legal_score": 1-10,
  "summary": ""
}
```

---

### 11. Deal Lead Agent (`dd-lead`)

**Purpose**: Synthesize all findings, calculate risk score, make recommendation.

**CLAUDE.md Instructions**:
```markdown
# Deal Lead - Investment Synthesis Agent

You are the deal lead responsible for synthesizing all due diligence findings.

## Your Role
- Review all specialist reports
- Identify critical issues vs minor concerns
- Calculate overall risk score
- Make investment recommendation
- Prepare Investment Committee briefing

## Risk Score Calculation
Weight each area:
- Founder/Team: 20%
- Market: 15%
- Competition: 10%
- Technology: 15%
- Business Model: 15%
- Traction: 15%
- Compliance: 5%
- Cap Table: 3%
- Legal: 2%

## Output Format
{
  "company_name": "",
  "funding_round": "",
  "risk_score": 0-100,  // Higher = riskier
  "risk_level": "low|medium|high|critical",
  "critical_issues": [],
  "key_concerns": [],
  "strengths": [],
  "recommendation": "strong-pass|pass|negotiate|invest|strong-invest",
  "recommended_terms": "",
  "investment_thesis": "",
  "deal_breakers": [],
  "executive_summary": ""
}
```

---

## Process Definition (YAML)

```yaml
name: vc-due-diligence
version: "1.0"
description: |
  Comprehensive multi-agent venture capital due diligence process.
  9 specialist agents analyze in parallel, synthesize findings,
  and deliver investment recommendation with human approval gate.

triggers:
  - type: manual
    id: start-diligence
  - type: webhook
    id: pitch-deck-submission

# =============================================================================
# STEPS
# =============================================================================
steps:

  # ---------------------------------------------------------------------------
  # PHASE 1: INTAKE
  # ---------------------------------------------------------------------------
  - id: intake
    type: agent_task
    name: "Parse Pitch Deck"
    agent: dd-intake
    message: |
      Parse the following pitch deck and extract structured data for due diligence.

      Company: {{input.company_name}}
      Pitch Deck URL: {{input.pitch_deck_url}}
      Additional Documents: {{input.additional_docs | default:'None provided'}}

      Extract all relevant information for the specialist agents.
    timeout: 10m
    retry:
      max_attempts: 2
      delay: 30s

  # ---------------------------------------------------------------------------
  # PHASE 2: PARALLEL ANALYSIS (9 agents simultaneously)
  # ---------------------------------------------------------------------------

  # Founder Analysis
  - id: founder-analysis
    type: agent_task
    name: "Founder Background Check"
    agent: dd-founder
    depends_on: [intake]
    message: |
      Conduct founder and team background checks.

      Company: {{input.company_name}}
      Founders: {{steps.intake.output.founders}}

      Research each founder thoroughly:
      - Verify all claims in the pitch deck
      - Check track record and previous ventures
      - Identify any red flags or controversies
      - Assess expertise fit for this venture
    timeout: 15m

  # Market Analysis
  - id: market-analysis
    type: agent_task
    name: "Market Research"
    agent: dd-market
    depends_on: [intake]
    message: |
      Validate market opportunity claims.

      Company: {{input.company_name}}
      Industry: {{steps.intake.output.industry}}
      Claimed TAM: {{steps.intake.output.claimed_tam}}

      Verify:
      - Total addressable market size
      - Growth rate (CAGR)
      - Market headwinds and tailwinds
      - Timing assessment
    timeout: 15m

  # Competitor Analysis
  - id: competitor-analysis
    type: agent_task
    name: "Competitive Landscape"
    agent: dd-competitor
    depends_on: [intake]
    message: |
      Map the competitive landscape.

      Company: {{input.company_name}}
      Industry: {{steps.intake.output.industry}}
      Competitors Mentioned: {{steps.intake.output.competitors_mentioned}}

      Research:
      - Direct and indirect competitors
      - Funding and traction comparison
      - Competitive moats and threats
      - Big tech encroachment risk
    timeout: 15m

  # Technology Assessment
  - id: tech-assessment
    type: agent_task
    name: "Technical Due Diligence"
    agent: dd-tech
    depends_on: [intake]
    message: |
      Assess technology and product.

      Company: {{input.company_name}}
      Product: {{steps.intake.output.product_description}}
      Tech Stack: {{steps.intake.output.tech_stack_mentioned}}

      Evaluate:
      - Problem-solution fit
      - Technology maturity and scalability
      - IP strength and protection
      - Security posture
    timeout: 15m

  # Business Model Analysis
  - id: bizmodel-analysis
    type: agent_task
    name: "Business Model Review"
    agent: dd-bizmodel
    depends_on: [intake]
    message: |
      Analyze business model sustainability.

      Company: {{input.company_name}}
      Product: {{steps.intake.output.product_description}}
      Revenue Model: {{input.revenue_model | default:'Not specified'}}

      Assess:
      - Revenue model viability
      - Unit economics
      - Scalability limits
      - Path to profitability
    timeout: 15m

  # Traction & Financials
  - id: traction-analysis
    type: agent_task
    name: "Traction & Financials"
    agent: dd-traction
    depends_on: [intake]
    message: |
      Verify traction and financial health.

      Company: {{input.company_name}}
      Claimed Revenue: {{steps.intake.output.claimed_revenue}}
      Claimed Growth: {{steps.intake.output.claimed_growth}}
      Financial Docs: {{input.financial_docs | default:'None provided'}}

      Verify:
      - Growth metrics accuracy
      - Burn rate and runway
      - Unit economics
      - Financial red flags
    timeout: 15m

  # Compliance Review
  - id: compliance-review
    type: agent_task
    name: "Regulatory Compliance"
    agent: dd-compliance
    depends_on: [intake]
    message: |
      Assess regulatory landscape and compliance.

      Company: {{input.company_name}}
      Industry: {{steps.intake.output.industry}}
      Markets: {{input.target_markets | default:'Not specified'}}

      Research:
      - Industry regulation level
      - Compliance requirements
      - Geographic expansion risks
      - Pending regulatory threats
    timeout: 15m

  # Cap Table Analysis
  - id: captable-analysis
    type: agent_task
    name: "Cap Table Review"
    agent: dd-captable
    depends_on: [intake]
    message: |
      Analyze cap table and equity structure.

      Company: {{input.company_name}}
      Cap Table: {{input.cap_table | default:'Not provided - research existing investors'}}

      Evaluate:
      - Founder dilution
      - Existing investor quality
      - Structure concerns
      - Future dilution risk
    timeout: 15m

  # Legal Review
  - id: legal-review
    type: agent_task
    name: "Legal Due Diligence"
    agent: dd-legal
    depends_on: [intake]
    message: |
      Conduct legal review.

      Company: {{input.company_name}}
      Legal Docs: {{input.legal_docs | default:'None provided'}}

      Review:
      - Corporate structure
      - IP ownership
      - Investor restrictions
      - Licensing and litigation
    timeout: 15m

  # ---------------------------------------------------------------------------
  # PHASE 3: SYNTHESIS
  # ---------------------------------------------------------------------------
  - id: risk-synthesis
    type: agent_task
    name: "Synthesize Findings"
    agent: dd-lead
    depends_on:
      - founder-analysis
      - market-analysis
      - competitor-analysis
      - tech-assessment
      - bizmodel-analysis
      - traction-analysis
      - compliance-review
      - captable-analysis
      - legal-review
    message: |
      Synthesize all due diligence findings for {{input.company_name}}.

      ## Specialist Reports

      ### Founder Analysis
      {{steps.founder-analysis.output}}

      ### Market Analysis
      {{steps.market-analysis.output}}

      ### Competitor Analysis
      {{steps.competitor-analysis.output}}

      ### Technology Assessment
      {{steps.tech-assessment.output}}

      ### Business Model
      {{steps.bizmodel-analysis.output}}

      ### Traction & Financials
      {{steps.traction-analysis.output}}

      ### Compliance
      {{steps.compliance-review.output}}

      ### Cap Table
      {{steps.captable-analysis.output}}

      ### Legal
      {{steps.legal-review.output}}

      ---

      Provide:
      1. Overall risk score (0-100)
      2. Critical issues that could be deal breakers
      3. Key strengths
      4. Investment recommendation
      5. Executive summary for Investment Committee
    timeout: 20m

  # ---------------------------------------------------------------------------
  # PHASE 4: HUMAN APPROVAL
  # ---------------------------------------------------------------------------
  - id: investment-committee
    type: human_approval
    name: "Investment Committee Review"
    depends_on: [risk-synthesis]
    title: "Investment Decision: {{input.company_name}}"
    description: |
      # Investment Committee Review

      ## Company: {{input.company_name}}
      **Funding Round**: {{input.funding_round}}
      **Ask**: {{input.funding_ask}}

      ---

      ## Executive Summary
      {{steps.risk-synthesis.output.executive_summary}}

      ---

      ## Risk Assessment

      | Metric | Score |
      |--------|-------|
      | **Overall Risk Score** | {{steps.risk-synthesis.output.risk_score}}/100 |
      | **Risk Level** | {{steps.risk-synthesis.output.risk_level}} |
      | **Recommendation** | {{steps.risk-synthesis.output.recommendation}} |

      ---

      ## Critical Issues
      {{steps.risk-synthesis.output.critical_issues}}

      ## Key Strengths
      {{steps.risk-synthesis.output.strengths}}

      ## Deal Breakers
      {{steps.risk-synthesis.output.deal_breakers}}

      ---

      ## Investment Thesis
      {{steps.risk-synthesis.output.investment_thesis}}

      ---

      **Please APPROVE to proceed with term sheet, or REJECT with feedback.**
    timeout: 72h
    timeout_action: skip

  # ---------------------------------------------------------------------------
  # PHASE 5: DECISION ROUTING
  # ---------------------------------------------------------------------------
  - id: decision-gate
    type: gateway
    name: "Route Decision"
    depends_on: [investment-committee]
    conditions:
      - expression: "{{steps.investment-committee.output.decision}} == 'approved'"
        next: prepare-term-sheet
      - default: true
        next: send-rejection

  # ---------------------------------------------------------------------------
  # PHASE 6: OUTCOMES
  # ---------------------------------------------------------------------------

  # Approved Path
  - id: prepare-term-sheet
    type: agent_task
    name: "Prepare Term Sheet"
    agent: dd-legal
    depends_on: [decision-gate]
    message: |
      Prepare term sheet for {{input.company_name}}.

      Investment Decision: APPROVED
      Committee Comments: {{steps.investment-committee.output.comments}}

      Risk Assessment: {{steps.risk-synthesis.output}}

      Draft term sheet with recommended terms and protections based on identified risks.
    timeout: 30m

  - id: notify-approval
    type: notification
    name: "Send Approval Notification"
    depends_on: [prepare-term-sheet]
    channels: [email, slack]
    message: |
      :white_check_mark: **Investment Approved**

      **Company**: {{input.company_name}}
      **Round**: {{input.funding_round}}

      Risk Score: {{steps.risk-synthesis.output.risk_score}}/100

      Term sheet prepared and ready for negotiation.
    recipients:
      - "#investments"
      - "{{input.deal_owner_email}}"

  # Rejected Path
  - id: send-rejection
    type: notification
    name: "Send Rejection Notice"
    depends_on: [decision-gate]
    channels: [email]
    message: |
      **Investment Decision: Pass**

      Company: {{input.company_name}}

      Risk Score: {{steps.risk-synthesis.output.risk_score}}/100

      Key Concerns:
      {{steps.risk-synthesis.output.critical_issues}}

      Committee Feedback:
      {{steps.investment-committee.output.comments | default:'Does not meet current investment criteria.'}}
    recipients:
      - "{{input.deal_owner_email}}"

# =============================================================================
# OUTPUTS
# =============================================================================
outputs:
  - name: company_name
    source: "{{input.company_name}}"
  - name: risk_score
    source: "{{steps.risk-synthesis.output.risk_score}}"
  - name: risk_level
    source: "{{steps.risk-synthesis.output.risk_level}}"
  - name: recommendation
    source: "{{steps.risk-synthesis.output.recommendation}}"
  - name: decision
    source: "{{steps.investment-committee.output.decision}}"
  - name: executive_summary
    source: "{{steps.risk-synthesis.output.executive_summary}}"
```

---

## System Manifest (Agent Fleet Deployment)

```yaml
name: vc-due-diligence-team
description: |
  AI Venture Capital Due Diligence Team
  9 specialist agents + 1 deal lead for comprehensive startup analysis

prompt: |
  You are part of a world-class venture capital due diligence team.

  Your mission: Provide thorough, unbiased analysis to help make
  informed investment decisions. Be rigorous. Be skeptical.
  Verify claims. Identify risks.

  When in doubt, dig deeper. When something seems too good to be true,
  it probably is. Your job is to find the truth, not validate pitches.

agents:
  # Intake Agent
  dd-intake:
    template: local:business-assistant
    resources:
      memory: "2g"
      cpu: "1"

  # Specialist Agents (run in parallel)
  dd-founder:
    template: local:business-assistant
    resources:
      memory: "4g"
      cpu: "2"

  dd-market:
    template: local:business-assistant
    resources:
      memory: "4g"
      cpu: "2"

  dd-competitor:
    template: local:business-assistant
    resources:
      memory: "4g"
      cpu: "2"

  dd-tech:
    template: local:business-assistant
    resources:
      memory: "4g"
      cpu: "2"

  dd-bizmodel:
    template: local:business-assistant
    resources:
      memory: "2g"
      cpu: "1"

  dd-traction:
    template: local:business-assistant
    resources:
      memory: "4g"
      cpu: "2"

  dd-compliance:
    template: local:business-assistant
    resources:
      memory: "2g"
      cpu: "1"

  dd-captable:
    template: local:business-assistant
    resources:
      memory: "2g"
      cpu: "1"

  dd-legal:
    template: local:business-assistant
    resources:
      memory: "4g"
      cpu: "2"

  # Deal Lead (synthesis)
  dd-lead:
    template: local:business-assistant
    resources:
      memory: "8g"
      cpu: "4"

permissions:
  preset: orchestrator-workers
  orchestrator: dd-lead
  # Deal lead can call all specialists
  # Specialists cannot call each other (parallel isolation)

folders:
  shared: true
  # All agents can write to shared folder for document handoff
```

---

## Demo Script (60 Seconds)

### Setup
1. Deploy agent fleet via system manifest
2. Create the process definition
3. Have a real pitch deck ready (or use sample)

### The Demo

**[0:00]** "Watch an AI VC firm analyze a startup."

**[0:05]** Upload pitch deck → Click "Start Due Diligence"

**[0:10]** Dashboard Timeline explodes:
- Intake agent parses deck
- 9 colored bars fan out simultaneously
- Each agent researching their domain

**[0:30]** Real-time activity:
- "Founder Agent: Checking LinkedIn..."
- "Market Agent: Verifying TAM claims..."
- "Competitor Agent: Found 7 competitors on Crunchbase..."

**[0:45]** Convergence:
- Specialist agents complete (bars turn green)
- Deal Lead starts synthesizing
- Risk score calculated

**[0:55]** Human moment:
- Approval notification appears
- Investment Committee review screen
- **One click: APPROVE or REJECT**

**[1:00]** "What takes VCs 2 weeks. 60 seconds. 9 agents."

---

## Process Inputs (API)

```json
{
  "company_name": "Acme AI Corp",
  "pitch_deck_url": "https://...",
  "funding_round": "Series A",
  "funding_ask": "$10M",
  "deal_owner_email": "partner@vcfirm.com",
  "additional_docs": "...",
  "financial_docs": "...",
  "cap_table": "...",
  "legal_docs": "...",
  "target_markets": ["US", "EU"],
  "revenue_model": "SaaS subscription"
}
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Total Process Time | < 60 seconds | Process execution duration |
| Parallel Efficiency | 9 agents simultaneously | Dashboard visualization |
| Human Touchpoints | 1 (Investment Committee) | Approval gate count |
| Research Depth | 9 domains covered | Specialist report completeness |
| Viral Potential | "Holy shit" reaction | User feedback |

---

## Next Steps

1. **Create Agent Templates**: Build CLAUDE.md for each specialist
2. **Deploy Fleet**: Use system manifest to spin up all 11 agents
3. **Create Process**: Deploy the YAML process definition
4. **Test with Sample Deck**: Run end-to-end with real pitch deck
5. **Record Demo**: Capture the 60-second magic for viral distribution

---

*"Your startup's fate. Decided by agents. In 60 seconds."*

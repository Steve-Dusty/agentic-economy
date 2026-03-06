---
name: dd-report-format
description: Standard output format for due diligence analysis reports. Use when producing your final analysis to ensure consistency across all specialist agents.
---

# Due Diligence Report Format

All specialist agents must output their analysis in this standardized JSON format. This enables automated synthesis by the Deal Lead agent.

## Standard Report Structure

```json
{
  "metadata": {
    "agent": "dd-{specialist}",
    "company": "Company Name",
    "analysis_date": "2024-01-15T10:30:00Z",
    "version": "1.0"
  },

  "executive_summary": {
    "headline": "One-sentence assessment",
    "recommendation": "POSITIVE | NEUTRAL | NEGATIVE | CRITICAL",
    "confidence": "HIGH | MEDIUM | LOW",
    "key_findings": [
      "Finding 1",
      "Finding 2",
      "Finding 3"
    ]
  },

  "risk_assessment": {
    "overall_score": 35,
    "category_scores": {
      "category_name": {
        "score": 30,
        "weight": 0.25,
        "rationale": "Brief explanation"
      }
    },
    "red_flags": [
      {
        "severity": "HIGH | MEDIUM | LOW",
        "description": "Description of the red flag",
        "evidence": "Supporting evidence",
        "mitigation": "Possible mitigation or none"
      }
    ],
    "green_flags": [
      {
        "description": "Positive indicator",
        "evidence": "Supporting evidence"
      }
    ]
  },

  "detailed_analysis": {
    "section_name": {
      "findings": "Detailed analysis text",
      "data": {},
      "sources": ["S1", "S2"]
    }
  },

  "sources": [
    {
      "id": "S1",
      "name": "Source name",
      "url": "URL",
      "tier": 1,
      "access_date": "2024-01-15"
    }
  ],

  "verification_summary": {
    "total_claims": 15,
    "verified": 10,
    "partially_verified": 3,
    "unverified": 1,
    "contradicted": 1
  },

  "follow_up_items": [
    {
      "priority": "HIGH | MEDIUM | LOW",
      "description": "Item requiring further investigation",
      "assigned_to": "dd-{specialist} or HUMAN"
    }
  ]
}
```

## Risk Scoring

Use a 0-100 scale where:
- **0-20**: Minimal risk (green light)
- **21-35**: Low risk (proceed with standard diligence)
- **36-50**: Moderate risk (proceed with caution)
- **51-70**: High risk (significant concerns)
- **71-100**: Critical risk (major red flags)

## File Naming Convention

Save your report to the shared folder as:
```
/shared-out/{your-domain}-analysis/{company_name}_{date}.json
```

Example:
```
/shared-out/founder-analysis/acme_corp_2024-01-15.json
```

## Markdown Summary

In addition to JSON, create a human-readable summary:
```
/shared-out/{your-domain}-analysis/{company_name}_{date}_summary.md
```

This should include:
- Executive summary (2-3 paragraphs)
- Key findings (bullet points)
- Risk assessment visualization
- Recommended actions

---
name: dd-sourcing
description: Document sources properly for due diligence reports. Use when citing any external data, ensuring full traceability and auditability of findings.
---

# Source Documentation Standards

All due diligence findings must be traceable to their sources. This enables audit trails, follow-up verification, and legal defensibility.

## Source Quality Tiers

### Tier 1: Primary Sources (Highest Credibility)
- SEC filings (10-K, 10-Q, S-1)
- Court documents and legal filings
- Government databases (USPTO, state registrations)
- Company's own audited financials
- Direct customer/reference interviews

### Tier 2: Secondary Sources (High Credibility)
- Established data providers (Crunchbase, PitchBook, CB Insights)
- Major news outlets (WSJ, Bloomberg, TechCrunch)
- Industry analyst reports (Gartner, Forrester)
- LinkedIn profiles (for employment verification)
- Academic research and papers

### Tier 3: Tertiary Sources (Use with Caution)
- Social media posts
- Blog articles
- Glassdoor reviews
- Wikipedia (only as starting point)
- Forum discussions

## Citation Format

Every fact must include a source citation:

```json
{
  "source": {
    "name": "Full source name",
    "type": "SEC_FILING | NEWS | DATA_PROVIDER | INTERVIEW | GOVERNMENT | OTHER",
    "url": "https://... (if available)",
    "access_date": "2024-01-15",
    "publication_date": "2024-01-10",
    "tier": 1,
    "excerpt": "Relevant quote or data point"
  }
}
```

## Best Practices

### DO:
- Capture URLs at time of access (pages change/disappear)
- Note the access date for all web sources
- Quote relevant passages, don't just link
- Use multiple sources for critical claims
- Prefer recent sources over older ones

### DON'T:
- Cite a source you haven't actually reviewed
- Use company press releases as independent verification
- Rely on a single source for material claims
- Cite sources behind paywalls without noting limitation
- Mix up "stated by company" vs "independently verified"

## Source Tracking in Output

Include a sources section in every analysis:

```json
{
  "sources_used": [
    {
      "id": "S1",
      "name": "Crunchbase - Acme Corp Profile",
      "url": "https://crunchbase.com/...",
      "access_date": "2024-01-15",
      "tier": 2,
      "used_for": ["funding_history", "employee_count"]
    }
  ],
  "source_statistics": {
    "tier_1": 3,
    "tier_2": 8,
    "tier_3": 2,
    "total": 13
  }
}
```

## Handling Source Conflicts

When sources disagree:
1. Note the discrepancy explicitly
2. Prefer higher-tier sources
3. Prefer more recent sources
4. Document both versions with reasoning for which to trust

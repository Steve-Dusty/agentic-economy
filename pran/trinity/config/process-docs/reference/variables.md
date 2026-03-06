# Variable Interpolation

Variables let you pass data between steps and inject dynamic values into your process definitions.

## Syntax

Variables use double-curly-brace syntax: `{{expression}}`

```yaml
message: |
  Analyze this topic: {{input.topic}}
  Use the research from: {{steps.research.output}}
```

## Variable Sources

### Input Variables

Access data passed when the process starts.

```yaml
# Access the entire input object
{{input}}

# Access specific input fields
{{input.topic}}
{{input.user.email}}
{{input.items[0].name}}
```

**Example trigger input:**
```json
{
  "topic": "Climate change",
  "user": { "email": "user@example.com" },
  "items": [{ "name": "Item 1" }]
}
```

### Step Output Variables

Reference output from completed steps.

```yaml
# Full step output
{{steps.research.output}}

# Nested fields (if output is structured)
{{steps.analyze.output.summary}}
{{steps.analyze.output.metrics.score}}
```

### Step Metadata Variables

Access step execution metadata.

```yaml
# Step status
{{steps.research.status}}

# Execution duration
{{steps.research.duration}}

# Start/end timestamps
{{steps.research.started_at}}
{{steps.research.completed_at}}
```

### Approval Step Variables

Human approval steps include decision data.

```yaml
# Decision: "approve" or "reject"
{{steps.review.output.decision}}

# Approver's comments
{{steps.review.output.comments}}

# Who approved
{{steps.review.output.approved_by}}
```

---

## Default Values

Provide fallback values for missing data.

```yaml
message: |
  Priority: {{input.priority | default:"normal"}}
  Tags: {{input.tags | default:[]}}
```

**Syntax:** `{{variable | default:value}}`

The default is used when:
- The variable doesn't exist
- The variable is `null`
- The variable is empty string (for strings)

---

## Conditional Output

Use gateway conditions to evaluate variables.

```yaml
- id: route
  type: gateway
  conditions:
    - expression: "{{steps.analyze.output.score}} > 80"
      next: high-quality-path
    - expression: "{{steps.analyze.output.score}} > 50"
      next: review-path
    - default: true
      next: reject-path
```

**Supported operators:**
| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equals | `{{x}} == 'value'` |
| `!=` | Not equals | `{{x}} != 'error'` |
| `>` | Greater than | `{{x}} > 10` |
| `>=` | Greater or equal | `{{x}} >= 0` |
| `<` | Less than | `{{x}} < 100` |
| `<=` | Less or equal | `{{x}} <= 50` |
| `contains` | String/array contains | `{{x}} contains 'urgent'` |

---

## Multiline Strings

Use YAML's `|` for multiline strings with variables.

```yaml
message: |
  Please analyze the following data:

  Topic: {{input.topic}}

  Previous research:
  {{steps.research.output}}

  Provide a detailed analysis covering:
  1. Key findings
  2. Trends
  3. Recommendations
```

**Tips:**
- `|` preserves newlines
- `>` folds newlines into spaces
- Indent continuation lines

---

## Variable in Different Contexts

### In Step Messages

```yaml
- id: analyze
  type: agent_task
  message: |
    Context: {{input.context}}
    Data: {{input.data}}
```

### In Approval Descriptions

```yaml
- id: review
  type: human_approval
  title: "Review: {{input.title}}"
  description: |
    Analysis result: {{steps.analyze.output}}
```

### In Outputs

```yaml
outputs:
  - name: final_report
    source: "{{steps.compile.output}}"
```

### In Gateway Conditions

```yaml
conditions:
  - expression: "{{steps.check.output.valid}} == true"
    next: proceed
```

---

## Accessing Nested Data

Navigate complex objects using dot notation.

```yaml
# Given this input:
# {
#   "user": {
#     "profile": {
#       "name": "Alice",
#       "roles": ["admin", "editor"]
#     }
#   }
# }

# Access nested fields
{{input.user.profile.name}}        # "Alice"

# Arrays use index notation
{{input.user.profile.roles[0]}}    # "admin"
```

---

## JSON Output Handling

When step output is JSON, you can access fields directly.

```yaml
# If steps.api.output is:
# {"status": "success", "data": {"count": 42}}

{{steps.api.output.status}}         # "success"
{{steps.api.output.data.count}}     # 42
```

**Note:** If the output is a string containing JSON, it needs to be parsed first. Use agent instructions to return structured data.

---

## Best Practices

### 1. Use Descriptive Names

```yaml
# Good
{{input.customer_email}}
{{steps.sentiment_analysis.output}}

# Avoid
{{input.e}}
{{steps.s1.output}}
```

### 2. Always Provide Defaults for Optional Data

```yaml
message: |
  Priority: {{input.priority | default:"medium"}}
  Notes: {{input.notes | default:"No additional notes"}}
```

### 3. Document Expected Input Structure

```yaml
# Expected input:
# {
#   "topic": "string - required",
#   "depth": "number - optional, defaults to 1",
#   "format": "string - optional, defaults to markdown"
# }
```

### 4. Handle Missing Steps Gracefully

If a step might be skipped (via gateway routing), use defaults:

```yaml
{{steps.optional_step.output | default:"Step was skipped"}}
```

---

## Troubleshooting

### Variable Not Resolved

If you see `{{steps.x.output}}` in the actual output:
- Check the step ID is correct (case-sensitive)
- Verify the step completed before this one (check `depends_on`)
- Ensure the step wasn't skipped by a gateway

### Null or Empty Values

- Use `| default:value` for fallbacks
- Check that the step actually returned output
- Verify the data structure matches your expectations

## Related

- [YAML Schema Reference](./yaml-schema)
- [Understanding Step Types](/processes/docs/getting-started/step-types)

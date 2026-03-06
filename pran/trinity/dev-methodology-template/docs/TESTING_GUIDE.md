# Testing Guide

> Guidelines for testing practices in this project.

---

## Philosophy

1. **Feature flows include testing instructions** — Follow them to verify features work
2. **Manual integration testing > automated tests** — For complex user journeys
3. **Automate when it saves time** — Repeated testing, regression prevention
4. **Test at the right level** — Unit for logic, integration for flows, E2E sparingly

---

## Test Tiers

### Tier 1: Smoke Tests (Fast)
**Duration**: ~1 minute
**Purpose**: Quick validation that nothing is catastrophically broken

Run when:
- Starting development
- Quick CI checks
- After dependency updates

```bash
# Example command (customize for your project)
npm run test:smoke
# or: pytest -m smoke
# or: go test -short ./...
```

### Tier 2: Core Tests (Standard)
**Duration**: ~5 minutes
**Purpose**: Comprehensive validation of core functionality

Run when:
- Before commits
- After feature changes
- Pre-PR validation

```bash
# Example command (customize for your project)
npm test
# or: pytest -m "not slow"
# or: go test ./...
```

### Tier 3: Full Suite (Comprehensive)
**Duration**: ~15+ minutes
**Purpose**: Complete validation including slow integration tests

Run when:
- Before releases
- After major refactoring
- Post-deployment verification

```bash
# Example command (customize for your project)
npm run test:all
# or: pytest -v
# or: go test -v ./...
```

---

## When to Write Tests

### Always Write Tests For:
- Bug fixes (regression prevention)
- Complex business logic
- Critical user paths
- Edge cases that have bitten you

### Consider Not Testing:
- Simple CRUD operations (covered by framework)
- UI styling
- Third-party library behavior
- One-off scripts

---

## Test Categories

### Unit Tests
Test individual functions and classes in isolation.

```
tests/unit/
├── services/
├── utils/
└── models/
```

**Characteristics:**
- Fast (milliseconds)
- No external dependencies
- Mock everything else

### Integration Tests
Test components working together.

```
tests/integration/
├── api/
├── database/
└── services/
```

**Characteristics:**
- Medium speed (seconds)
- May use test database
- Real HTTP calls to local server

### End-to-End Tests
Test complete user journeys.

```
tests/e2e/
├── user-flows/
└── critical-paths/
```

**Characteristics:**
- Slow (minutes)
- Real browser or API client
- Full system running

---

## Feature Flow Testing

Each feature flow document (`docs/memory/feature-flows/*.md`) should include a Testing section:

```markdown
## Testing

**Prerequisites**:
- [ ] Application running
- [ ] Test user created
- [ ] Test data seeded

**Test Steps**:

### 1. Happy Path
**Action**: [What to do]
**Expected**: [What should happen]
**Verify**:
- [ ] Check 1
- [ ] Check 2

### 2. Error Cases
**Action**: [Invalid input]
**Expected**: [Error message]

**Edge Cases**:
- [ ] Empty input
- [ ] Very long input
- [ ] Special characters

**Last Tested**: YYYY-MM-DD
**Status**: ✅ Working
```

---

## Running Tests

### Using the test-runner Agent

Ask Claude Code:
```
Run the tests
```

Or specify a tier:
```
Run smoke tests
Run the full test suite
```

### Manual Commands

```bash
# Run all tests
npm test

# Run specific file
npm test -- path/to/test.spec.js

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

---

## Quality Thresholds

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Pass Rate | >90% | 75-90% | <75% |
| Failures | 0 | 1-5 | >5 |
| Coverage | >80% | 60-80% | <60% |

---

## Test Data

### Fixtures
Store reusable test data in `tests/fixtures/`:

```
tests/fixtures/
├── users.json
├── products.json
└── orders.json
```

### Factories
Use factories for dynamic test data:

```javascript
const createUser = (overrides = {}) => ({
  name: 'Test User',
  email: 'test@example.com',
  ...overrides
});
```

### Cleanup
Always clean up after tests:

```javascript
afterEach(async () => {
  await db.users.deleteMany({ email: /@example.com$/ });
});
```

---

## Mocking

### When to Mock
- External APIs
- Time-dependent functions
- Random/non-deterministic behavior
- Slow operations

### When Not to Mock
- Your own code (usually)
- Database (use test DB instead)
- File system (use temp directories)

---

## CI/CD Integration

### Pre-commit
```bash
# .git/hooks/pre-commit
npm run test:smoke
```

### Pull Request
```yaml
# Run core tests on every PR
on: pull_request
steps:
  - run: npm test
```

### Main Branch
```yaml
# Run full suite on merge to main
on:
  push:
    branches: [main]
steps:
  - run: npm run test:all
```

---

## Debugging Failed Tests

1. **Read the error message** — Often tells you exactly what's wrong
2. **Check test isolation** — Tests shouldn't depend on each other
3. **Look at recent changes** — What code changed?
4. **Run in isolation** — Does it fail by itself?
5. **Add logging** — Temporarily add console.log
6. **Check fixtures** — Is test data correct?

---

## Best Practices

### DO
- ✅ Write descriptive test names
- ✅ Test one thing per test
- ✅ Use descriptive assertions
- ✅ Clean up after tests
- ✅ Run tests frequently

### DON'T
- ❌ Test implementation details
- ❌ Share state between tests
- ❌ Skip flaky tests indefinitely
- ❌ Mock everything
- ❌ Write tests after the fact (unless for bugs)

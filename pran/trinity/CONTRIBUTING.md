# Contributing to Trinity

Thank you for your interest in contributing to Trinity! This document provides guidelines for contributing to the project.

## License

By contributing to Trinity, you agree that your contributions will be licensed under the [Polyform Noncommercial License 1.0.0](LICENSE).

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## How to Contribute

### Reporting Bugs

1. Check if the issue already exists in [GitHub Issues](https://github.com/abilityai/trinity/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Docker version, etc.)
   - Relevant logs or screenshots

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the use case and problem you're solving
3. Propose a solution (optional)
4. Be open to discussion and alternatives

### Pull Requests

1. **Fork and clone** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following our coding standards
4. **Test your changes** locally
5. **Commit with clear messages**:
   ```bash
   git commit -m "feat: Add support for custom metrics"
   ```
6. **Push and create a PR** against `main`

### Commit Message Format

We use conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Formatting, no code change
- `refactor:` Code change that neither fixes nor adds
- `test:` Adding tests
- `chore:` Maintenance tasks

Examples:
```
feat: Add agent custom metrics API
fix: Correct context percentage calculation
docs: Update deployment guide for production
```

## Development Setup

### Prerequisites

- Docker and Docker Compose v2+
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### Local Development

```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/trinity.git
cd trinity

# 2. Configure environment
cp .env.example .env
# Edit .env with required values

# 3. Build base image
./scripts/deploy/build-base-image.sh

# 4. Start services
./scripts/deploy/start.sh

# 5. Access the platform
# Web UI: http://localhost:3000
# API: http://localhost:8000/docs
```

### Running Tests

```bash
# Backend tests
cd tests
python -m pytest -v

# Frontend (if applicable)
cd src/frontend
npm run test
```

## Code Standards

### Python (Backend)

- Follow PEP 8
- Use type hints
- Document public functions with docstrings
- Keep functions focused and small

### TypeScript/JavaScript (Frontend, MCP Server)

- Use TypeScript for new code
- Follow existing code style
- Use meaningful variable names
- Add comments for complex logic

### Vue.js (Frontend)

- Use Composition API
- Follow Vue.js style guide
- Keep components focused
- Use Pinia for state management

## Project Structure

```
trinity/
├── src/
│   ├── backend/          # FastAPI - Python
│   ├── frontend/         # Vue.js 3 - TypeScript
│   ├── mcp-server/       # MCP Server - TypeScript
│   └── audit-logger/     # Audit Service - Python
├── docker/
│   ├── base-image/       # Agent base image
│   └── ...               # Service Dockerfiles
├── config/               # Configuration files
├── docs/                 # Documentation
└── tests/                # Test suite
```

## Areas for Contribution

### Good First Issues

Look for issues labeled `good first issue` - these are suitable for newcomers.

### Feature Development

- Agent template improvements
- UI/UX enhancements
- MCP tool additions
- Documentation improvements
- Test coverage

### Documentation

- Improve existing docs
- Add examples and tutorials
- Fix typos and clarify language
- Translate to other languages

## Questions?

- Open a [Discussion](https://github.com/abilityai/trinity/discussions) for questions
- Join our community (link coming soon)
- Email: [hello@ability.ai](mailto:hello@ability.ai)

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Special thanks section (for major features)

Thank you for contributing to Trinity!

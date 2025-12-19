# Contributing to TruePulse

Thank you for your interest in contributing to TruePulse! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. **Search existing issues** to avoid duplicates
2. **Use the bug report template** when creating new issues
3. **Include**:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, browser, etc.)

### Suggesting Features

1. **Check the roadmap** and existing feature requests
2. **Use the feature request template**
3. **Explain**:
   - The problem you're trying to solve
   - Your proposed solution
   - Alternative approaches considered

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding standards** (see below)
3. **Write tests** for new functionality
4. **Update documentation** as needed
5. **Ensure CI passes** before requesting review

## Development Setup

### Prerequisites

```bash
# Required
- Python 3.11+
- Node.js 20+
- Docker (optional, for local services)

# Recommended
- VS Code with recommended extensions
- Azure CLI (for deployment testing)
```

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/TruePulse.git
cd TruePulse

# Create a feature branch
git checkout -b feature/your-feature-name

# Backend setup
cd src/backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Unix
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend setup
cd ../frontend
npm install

# Run tests
cd ../backend && pytest
cd ../frontend && npm test
```

## Coding Standards

### Python (Backend)

- **Style**: Follow PEP 8, enforced by `ruff`
- **Type Hints**: Required for all function signatures
- **Docstrings**: Google style for public APIs
- **Testing**: pytest with minimum 80% coverage

```python
# Example
async def create_poll(
    poll_data: PollCreate,
    current_user: User = Depends(get_current_user),
) -> Poll:
    """Create a new poll.
    
    Args:
        poll_data: The poll creation data.
        current_user: The authenticated user.
        
    Returns:
        The created poll instance.
        
    Raises:
        HTTPException: If the user doesn't have permission.
    """
    ...
```

### TypeScript (Frontend)

- **Style**: Follow ESLint configuration
- **Types**: Strict TypeScript, no `any`
- **Components**: Functional components with hooks
- **Testing**: Jest with React Testing Library

```typescript
// Example
interface PollCardProps {
  poll: Poll;
  onVote: (choice: string) => Promise<void>;
}

export function PollCard({ poll, onVote }: PollCardProps) {
  // Implementation
}
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat(polls): add daily poll scheduling
fix(auth): resolve token refresh race condition
docs(api): update enterprise endpoint documentation
```

## Architecture Guidelines

### Backend

- **Clean Architecture**: Separate concerns into layers
- **Dependency Injection**: Use FastAPI's dependency system
- **Repository Pattern**: Abstract database operations
- **Service Layer**: Business logic in services, not routes

### Frontend

- **Component Composition**: Small, reusable components
- **Server Components**: Prefer RSC where possible
- **Client State**: Use React Query for server state
- **Form Handling**: React Hook Form with Zod validation

### Security

- **Never commit secrets** (use environment variables)
- **Validate all inputs** (server-side required)
- **Use parameterized queries** (prevent SQL injection)
- **Follow OWASP guidelines** for web security

## Testing

### Required Coverage

- Backend: 80% minimum
- Frontend: 70% minimum
- Critical paths: 100%

### Test Types

```bash
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration

# End-to-end tests
npm run test:e2e
```

## Review Process

1. **Automated Checks**: CI must pass
2. **Code Review**: At least one maintainer approval
3. **Security Review**: For security-sensitive changes
4. **Documentation Review**: For API changes

## Getting Help

- **Discord**: [Join our community](https://discord.gg/truepulse)
- **Discussions**: GitHub Discussions for questions
- **Issues**: For bugs and feature requests

## Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- Annual contributor report

Thank you for contributing to TruePulse! 🎉

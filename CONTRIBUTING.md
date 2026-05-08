# Contributing to NetFlow Anomaly Detection Server

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/netflow-anomaly-detection-server.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `make test`
6. Commit your changes: `git commit -am 'Add some feature'`
7. Push to the branch: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install development dependencies
make dev-install

# Run in development mode
make run
```

## Code Style

- Follow PEP 8 for Python code
- Use type hints where applicable
- Format code with Black: `make format`
- Check linting: `make lint`
- Maximum line length: 127 characters

## Testing

- Write tests for new features
- Ensure all tests pass: `make test`
- Maintain or improve code coverage
- Test edge cases and error conditions

## Commit Messages

Follow conventional commit format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Example: `feat: add real-time anomaly alerting`

## Pull Request Guidelines

- Keep PRs focused on a single feature/fix
- Update documentation as needed
- Add tests for new functionality
- Ensure CI passes
- Provide clear description of changes
- Reference related issues

## Code Review Process

1. Automated checks must pass (CI, linting, tests)
2. At least one maintainer approval required
3. Address review feedback
4. Squash commits before merge if requested

## Reporting Issues

When reporting issues, please include:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

## Feature Requests

- Open an issue with `[Feature Request]` prefix
- Describe the use case
- Explain expected benefits
- Consider implementation complexity

## Questions?

Open a discussion or reach out to maintainers.

Thank you for contributing! 🎉

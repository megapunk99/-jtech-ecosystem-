# Common Rules — All Languages

These rules apply to every project regardless of language or framework.

## File Structure

- One file = one responsibility
- Max 300 lines per file
- Max 3 levels of nesting
- Descriptive names over abbreviations

## Error Handling

- Handle ALL error cases, not just the happy path
- Log errors with context, not just the message
- Never swallow exceptions silently
- Provide meaningful error messages to users

## Testing

- Every public function needs a test
- Test edge cases: empty input, null values, boundary conditions
- Tests must be deterministic (no random failures)
- One assertion per test case

## Security

- Never hardcode secrets, API keys, or credentials
- Validate ALL user input
- Use parameterized queries, not string interpolation
- Apply principle of least privilege

## Performance

- Lazy loading over eager loading
- Cache expensive operations
- Batch database operations where possible
- Profile before optimizing

## Documentation

- Public APIs need docstrings/comments
- Complex logic needs inline explanation
- Keep README updated with setup instructions
- Document trade-offs and design decisions

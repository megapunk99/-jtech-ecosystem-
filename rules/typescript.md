# TypeScript Rules

## Style

- Strict mode enabled — no implicit any
- Use interfaces over types for objects
- Use type aliases for unions and primitives
- PascalCase for types, camelCase for variables
- Prefer `const` over `let`, never use `var`

## React Components

```typescript
// Functional component with proper types
interface Props {
  name: string;
  onAction: (id: string) => void;
}

export function MyComponent({ name, onAction }: Props) {
  return <div onClick={() => onAction(name)}>{name}</div>;
}
```

## State Management

- Use React hooks (useState, useEffect, useCallback)
- Custom hooks for reusable state logic
- Avoid class components in new code
- Use context sparingly — prefer prop drilling for simple cases

## File Structure

```
src/
├── components/     # React components
├── hooks/          # Custom hooks
├── lib/            # Utility functions
├── types/          # TypeScript type definitions
├── api/            # API client code
└── App.tsx         # Main app component
```

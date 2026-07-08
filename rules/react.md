# React Rules

## Component Patterns

- Functional components only — no class components
- Use `export function` over `export default` for named exports
- One component per file, unless tightly coupled
- Keep components under 150 lines

## Hooks

```typescript
// Custom hooks start with 'use'
export function useUser(id: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUser(id).then(u => {
      setUser(u);
      setLoading(false);
    });
  }, [id]);

  return { user, loading };
}
```

## State Management

- Local state: `useState` for simple values, `useReducer` for complex state
- Server state: Custom hooks with loading/error/data pattern
- Global state: React Context for theme/auth, avoid for data
- Cache: `useMemo` and `useCallback` only when profiling shows benefit

## Performance

- `React.memo` for pure components that re-render often
- `useMemo` for expensive computations
- `useCallback` for stable function references
- Lazy load route components with `React.lazy` and `Suspense`

## Styling

- Tailwind CSS utility classes for all styling
- No CSS modules or styled-components in new code
- Use `cn()` utility for conditional classes
- Responsive design with Tailwind breakpoints (`sm:`, `md:`, `lg:`, `xl:`)

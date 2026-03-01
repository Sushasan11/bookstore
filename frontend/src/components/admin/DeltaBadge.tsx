export function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null || delta === 0) {
    return <span className="text-muted-foreground text-sm">— 0%</span>
  }
  if (delta > 0) {
    return (
      <span className="text-green-600 dark:text-green-400 text-sm font-medium">
        ▲ {delta.toFixed(1)}%
      </span>
    )
  }
  return (
    <span className="text-red-600 dark:text-red-400 text-sm font-medium">
      ▼ {Math.abs(delta).toFixed(1)}%
    </span>
  )
}

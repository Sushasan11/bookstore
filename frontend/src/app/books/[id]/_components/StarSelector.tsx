'use client'

import { useState } from 'react'

interface StarSelectorProps {
  value: number          // 1-5, 0 = unset
  onChange: (rating: number) => void
  disabled?: boolean
}

export function StarSelector({ value, onChange, disabled }: StarSelectorProps) {
  const [hovered, setHovered] = useState(0)
  const display = hovered || value

  return (
    <div className="flex gap-1" role="group" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled}
          onClick={() => onChange(star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          aria-label={`${star} star${star !== 1 ? 's' : ''}`}
          className={[
            'text-2xl transition-colors',
            star <= display ? 'text-yellow-500' : 'text-muted-foreground',
            disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
          ].join(' ')}
        >
          ★
        </button>
      ))}
    </div>
  )
}

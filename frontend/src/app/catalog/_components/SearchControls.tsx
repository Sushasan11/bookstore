'use client'

import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import { useDebouncedCallback } from 'use-debounce'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import type { GenreResponse } from '@/lib/catalog'

type PriceRange = {
  label: string
  min?: number
  max?: number
}

const PRICE_RANGES: PriceRange[] = [
  { label: 'Any Price' },
  { label: '$0–$10', min: 0, max: 10 },
  { label: '$10–$25', min: 10, max: 25 },
  { label: '$25–$50', min: 25, max: 50 },
  { label: '$50+', min: 50 },
]

type SortOption = {
  label: string
  sort?: string
  sort_dir?: 'asc' | 'desc'
}

const SORT_OPTIONS: SortOption[] = [
  { label: 'Relevance' },
  { label: 'Price: Low to High', sort: 'price', sort_dir: 'asc' },
  { label: 'Price: High to Low', sort: 'price', sort_dir: 'desc' },
  { label: 'Newest', sort: 'created_at' },
  { label: 'Highest Rated', sort: 'avg_rating', sort_dir: 'desc' },
]

function getSortValue(sort?: string | null, sort_dir?: string | null): string {
  if (!sort) return 'relevance'
  if (sort === 'price' && sort_dir === 'asc') return 'price_asc'
  if (sort === 'price' && sort_dir === 'desc') return 'price_desc'
  if (sort === 'created_at') return 'created_at'
  if (sort === 'avg_rating') return 'avg_rating'
  return 'relevance'
}

function sortValueToParams(value: string): { sort?: string; sort_dir?: 'asc' | 'desc' } {
  switch (value) {
    case 'price_asc':
      return { sort: 'price', sort_dir: 'asc' }
    case 'price_desc':
      return { sort: 'price', sort_dir: 'desc' }
    case 'created_at':
      return { sort: 'created_at' }
    case 'avg_rating':
      return { sort: 'avg_rating', sort_dir: 'desc' }
    default:
      return {}
  }
}

interface SearchControlsProps {
  genres: GenreResponse[]
}

export function SearchControls({ genres }: SearchControlsProps) {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()

  function updateParams(updates: Record<string, string | undefined>) {
    const params = new URLSearchParams(searchParams.toString())
    // Always reset page when filters change
    params.set('page', '1')
    for (const [key, value] of Object.entries(updates)) {
      if (value === undefined || value === '') {
        params.delete(key)
      } else {
        params.set(key, value)
      }
    }
    router.replace(`${pathname}?${params.toString()}`)
  }

  const handleSearch = useDebouncedCallback((value: string) => {
    updateParams({ q: value || undefined })
  }, 300)

  function handleGenreChange(value: string) {
    updateParams({ genre_id: value || undefined })
  }

  function handlePriceRange(range: PriceRange) {
    updateParams({
      min_price: range.min !== undefined ? String(range.min) : undefined,
      max_price: range.max !== undefined ? String(range.max) : undefined,
    })
  }

  function handleSortChange(value: string) {
    const { sort, sort_dir } = sortValueToParams(value)
    updateParams({
      sort: sort,
      sort_dir: sort_dir,
    })
  }

  const currentMinPrice = searchParams.get('min_price')
  const currentMaxPrice = searchParams.get('max_price')
  const currentSort = searchParams.get('sort')
  const currentSortDir = searchParams.get('sort_dir')
  const currentSortValue = getSortValue(currentSort, currentSortDir)
  const currentGenreId = searchParams.get('genre_id') ?? ''

  function isPriceRangeActive(range: PriceRange): boolean {
    if (!range.min && !range.max) {
      return !currentMinPrice && !currentMaxPrice
    }
    const minMatch =
      range.min !== undefined ? currentMinPrice === String(range.min) : !currentMinPrice
    const maxMatch =
      range.max !== undefined ? currentMaxPrice === String(range.max) : !currentMaxPrice
    return minMatch && maxMatch
  }

  return (
    <div className="flex flex-wrap gap-3 mb-6">
      {/* Search input */}
      <div className="flex-1 min-w-[200px]">
        <Input
          placeholder="Search by title, author, or genre..."
          defaultValue={searchParams.get('q') ?? ''}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full"
        />
      </div>

      {/* Genre filter */}
      <div className="min-w-[160px]">
        <Select value={currentGenreId} onValueChange={handleGenreChange}>
          <SelectTrigger>
            <SelectValue placeholder="All Genres" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Genres</SelectItem>
            {genres.map((genre) => (
              <SelectItem key={genre.id} value={String(genre.id)}>
                {genre.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Sort dropdown */}
      <div className="min-w-[180px]">
        <Select value={currentSortValue} onValueChange={handleSortChange}>
          <SelectTrigger>
            <SelectValue placeholder="Sort by..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="relevance">Relevance</SelectItem>
            <SelectItem value="price_asc">Price: Low to High</SelectItem>
            <SelectItem value="price_desc">Price: High to Low</SelectItem>
            <SelectItem value="created_at">Newest</SelectItem>
            <SelectItem value="avg_rating">Highest Rated</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Price range presets */}
      <div className="flex flex-wrap gap-1 items-center">
        {PRICE_RANGES.map((range) => (
          <Button
            key={range.label}
            variant={isPriceRangeActive(range) ? 'default' : 'outline'}
            size="sm"
            onClick={() => handlePriceRange(range)}
          >
            {range.label}
          </Button>
        ))}
      </div>
    </div>
  )
}

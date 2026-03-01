'use client'

import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Upload } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { uploadImage } from '@/lib/admin'
import type { components } from '@/types/api.generated'

type BookResponse = components['schemas']['BookResponse']
type GenreResponse = components['schemas']['GenreResponse']

const bookSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  author: z.string().min(1, 'Author is required'),
  price: z
    .string()
    .min(1, 'Price is required')
    .regex(/^\d+(\.\d{1,2})?$/, 'Invalid price (e.g. 9.99)'),
  isbn: z.string().optional().or(z.literal('')),
  genre_id: z.union([z.number(), z.literal('')]).optional(),
  description: z.string().optional().or(z.literal('')),
  cover_image_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  publish_date: z.string().optional().or(z.literal('')),
})

export type BookFormValues = z.infer<typeof bookSchema>

function bookToFormValues(book: BookResponse): BookFormValues {
  return {
    title: book.title,
    author: book.author,
    price: book.price,
    isbn: book.isbn ?? '',
    genre_id: book.genre_id ?? '',
    description: book.description ?? '',
    cover_image_url: book.cover_image_url ?? '',
    publish_date: book.publish_date ?? '',
  }
}

interface BookFormProps {
  book?: BookResponse | null
  genres: GenreResponse[]
  onSubmit: (data: BookFormValues) => void
  onCancel: () => void
  isPending?: boolean
  accessToken: string
}

export function BookForm({ book, genres, onSubmit, onCancel, isPending, accessToken }: BookFormProps) {
  const [imageMode, setImageMode] = useState<'url' | 'upload'>('url')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const form = useForm<BookFormValues>({
    resolver: zodResolver(bookSchema),
    defaultValues: {
      title: '',
      author: '',
      price: '',
      isbn: '',
      genre_id: '',
      description: '',
      cover_image_url: '',
      publish_date: '',
    },
  })

  useEffect(() => {
    if (book) {
      form.reset(bookToFormValues(book))
    } else {
      form.reset({
        title: '',
        author: '',
        price: '',
        isbn: '',
        genre_id: '',
        description: '',
        cover_image_url: '',
        publish_date: '',
      })
    }
  }, [book, form])

  const isEditing = !!book
  const coverUrl = form.watch('cover_image_url')
  const genreId = form.watch('genre_id')

  async function handleFileUpload(file: File) {
    setUploading(true)
    try {
      const { url } = await uploadImage(accessToken, file)
      form.setValue('cover_image_url', url, { shouldValidate: true })
      toast.success('Image uploaded')
    } catch {
      toast.error('Failed to upload image')
    } finally {
      setUploading(false)
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4 px-4 pb-4">
      {/* Title */}
      <div className="space-y-1.5">
        <Label htmlFor="title">
          Title <span className="text-red-500">*</span>
        </Label>
        <Input id="title" {...form.register('title')} />
        {form.formState.errors.title && (
          <p className="text-sm text-red-500">{form.formState.errors.title.message}</p>
        )}
      </div>

      {/* Author */}
      <div className="space-y-1.5">
        <Label htmlFor="author">
          Author <span className="text-red-500">*</span>
        </Label>
        <Input id="author" {...form.register('author')} />
        {form.formState.errors.author && (
          <p className="text-sm text-red-500">{form.formState.errors.author.message}</p>
        )}
      </div>

      {/* Price */}
      <div className="space-y-1.5">
        <Label htmlFor="price">
          Price <span className="text-red-500">*</span>
        </Label>
        <Input id="price" type="text" placeholder="9.99" {...form.register('price')} />
        {form.formState.errors.price && (
          <p className="text-sm text-red-500">{form.formState.errors.price.message}</p>
        )}
      </div>

      {/* ISBN */}
      <div className="space-y-1.5">
        <Label htmlFor="isbn">ISBN</Label>
        <Input id="isbn" {...form.register('isbn')} />
        {form.formState.errors.isbn && (
          <p className="text-sm text-red-500">{form.formState.errors.isbn.message}</p>
        )}
      </div>

      {/* Genre — key forces re-mount when book or genres change so Radix Select picks up the new value */}
      <div className="space-y-1.5">
        <Label>Genre</Label>
        <Select
          key={`genre-${book?.id ?? 'new'}-${genres.length}`}
          value={
            genreId !== undefined && genreId !== ''
              ? String(genreId)
              : 'none'
          }
          onValueChange={(value) => {
            form.setValue('genre_id', value === 'none' ? '' : Number(value))
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="No Genre" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">No Genre</SelectItem>
            {genres.map((genre) => (
              <SelectItem key={genre.id} value={String(genre.id)}>
                {genre.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {form.formState.errors.genre_id && (
          <p className="text-sm text-red-500">{form.formState.errors.genre_id.message}</p>
        )}
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <Label htmlFor="description">Description</Label>
        <Textarea id="description" {...form.register('description')} />
        {form.formState.errors.description && (
          <p className="text-sm text-red-500">{form.formState.errors.description.message}</p>
        )}
      </div>

      {/* Cover Image — dual mode: URL or Upload */}
      <div className="space-y-1.5">
        <Label>Cover Image</Label>
        <div className="flex gap-1 mb-2">
          <Button
            type="button"
            variant={imageMode === 'url' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setImageMode('url')}
          >
            URL
          </Button>
          <Button
            type="button"
            variant={imageMode === 'upload' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setImageMode('upload')}
          >
            <Upload className="h-4 w-4 mr-1" />
            Upload
          </Button>
        </div>

        {imageMode === 'url' ? (
          <Input
            id="cover_image_url"
            type="url"
            placeholder="https://..."
            {...form.register('cover_image_url')}
          />
        ) : (
          <div className="flex gap-2">
            <Input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={uploading}
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleFileUpload(file)
              }}
            />
            {uploading && <p className="text-sm text-muted-foreground self-center">Uploading...</p>}
          </div>
        )}

        {form.formState.errors.cover_image_url && (
          <p className="text-sm text-red-500">{form.formState.errors.cover_image_url.message}</p>
        )}

        {/* Image preview */}
        {coverUrl && coverUrl !== '' && (
          <div className="mt-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={coverUrl}
              alt="Cover preview"
              className="h-32 w-auto rounded border object-contain"
              onError={(e) => {
                ;(e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          </div>
        )}
      </div>

      {/* Publish Date */}
      <div className="space-y-1.5">
        <Label htmlFor="publish_date">Publish Date</Label>
        <Input id="publish_date" type="date" {...form.register('publish_date')} />
        {form.formState.errors.publish_date && (
          <p className="text-sm text-red-500">{form.formState.errors.publish_date.message}</p>
        )}
      </div>

      {/* Footer buttons */}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isPending}>
          Cancel
        </Button>
        <Button type="submit" disabled={isPending || uploading}>
          {isPending ? (isEditing ? 'Saving...' : 'Adding...') : isEditing ? 'Save Changes' : 'Add Book'}
        </Button>
      </div>
    </form>
  )
}

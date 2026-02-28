import { BookOpen } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export default function CatalogPage() {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Card className="max-w-md w-full">
        <CardContent className="flex flex-col items-center gap-4 pt-8 pb-8 text-center">
          <BookOpen className="h-12 w-12 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Book Catalog</h2>
          <p className="text-muted-foreground">
            Catalog management with CRUD operations is coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

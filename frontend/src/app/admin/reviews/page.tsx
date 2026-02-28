import { Star } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export default function ReviewsPage() {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Card className="max-w-md w-full">
        <CardContent className="flex flex-col items-center gap-4 pt-8 pb-8 text-center">
          <Star className="h-12 w-12 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Review Moderation</h2>
          <p className="text-muted-foreground">
            Review moderation and management is coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

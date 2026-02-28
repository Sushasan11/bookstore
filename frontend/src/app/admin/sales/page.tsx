import { TrendingUp } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export default function SalesPage() {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Card className="max-w-md w-full">
        <CardContent className="flex flex-col items-center gap-4 pt-8 pb-8 text-center">
          <TrendingUp className="h-12 w-12 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Sales Analytics</h2>
          <p className="text-muted-foreground">
            Detailed sales reports and analytics are coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

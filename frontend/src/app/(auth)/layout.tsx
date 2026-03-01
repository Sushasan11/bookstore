import { BookStoreLogo } from '@/components/brand/BookStoreLogo'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-6">
          <BookStoreLogo iconSize={36} textClassName="text-xl font-bold" />
        </div>
        {children}
      </div>
    </div>
  )
}

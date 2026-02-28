'use client'

import { useSession, signOut } from 'next-auth/react'
import { SidebarMenuButton, SidebarMenuItem, SidebarMenu, useSidebar } from '@/components/ui/sidebar'
import { LogOut, User } from 'lucide-react'

export function SidebarFooterUser() {
  const { data: session } = useSession()
  const { state } = useSidebar()
  const email = session?.user?.email ?? ''

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton size="lg" tooltip={email}>
          <User className="h-4 w-4 shrink-0" />
          {state === 'expanded' && (
            <span className="truncate text-sm">{email}</span>
          )}
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem>
        <SidebarMenuButton onClick={() => signOut({ callbackUrl: '/' })} tooltip="Sign Out">
          <LogOut className="h-4 w-4" />
          {state === 'expanded' && <span>Sign Out</span>}
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}

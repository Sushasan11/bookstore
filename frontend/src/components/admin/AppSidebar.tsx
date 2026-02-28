'use client'

import { usePathname } from 'next/navigation'
import {
  Sidebar, SidebarContent, SidebarHeader, SidebarFooter,
  SidebarMenu, SidebarMenuItem, SidebarMenuButton, SidebarGroup, SidebarGroupContent,
} from '@/components/ui/sidebar'
import { LayoutDashboard, TrendingUp, BookOpen, Package, Users, Star, ChevronLeft } from 'lucide-react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { SidebarFooterUser } from './SidebarFooterUser'

const navItems = [
  { href: '/admin/overview', label: 'Overview', icon: LayoutDashboard },
  { href: '/admin/sales', label: 'Sales', icon: TrendingUp },
  { href: '/admin/catalog', label: 'Catalog', icon: BookOpen },
  { href: '/admin/inventory', label: 'Inventory', icon: Package },
  { href: '/admin/users', label: 'Users', icon: Users },
  { href: '/admin/reviews', label: 'Reviews', icon: Star },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5">
          <span className="font-bold text-lg group-data-[collapsible=icon]:hidden">BookStore</span>
          <Badge variant="secondary" className="text-xs group-data-[collapsible=icon]:hidden">Admin</Badge>
        </div>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip="Back to Store">
              <Link href="/">
                <ChevronLeft className="h-4 w-4" />
                <span>Back to Store</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname.startsWith(item.href)}
                    tooltip={item.label}
                  >
                    <Link href={item.href}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.label}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarFooterUser />
      </SidebarFooter>
    </Sidebar>
  )
}

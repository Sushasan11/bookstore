'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { type ColumnDef } from '@tanstack/react-table'
import { MoreHorizontal } from 'lucide-react'
import { toast } from 'sonner'
import { adminKeys, fetchAdminUsers, deactivateUser, reactivateUser } from '@/lib/admin'
import { ApiError } from '@/lib/api'
import { DataTable } from '@/components/admin/DataTable'
import { AdminPagination } from '@/components/admin/AdminPagination'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { components } from '@/types/api.generated'

type AdminUserResponse = components['schemas']['AdminUserResponse']

const PAGE_SIZE = 20

function RoleBadge({ role }: { role: string }) {
  if (role === 'admin') {
    return (
      <Badge className="bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400">
        Admin
      </Badge>
    )
  }
  return (
    <Badge className="bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400">
      User
    </Badge>
  )
}

function ActiveBadge({ isActive }: { isActive: boolean }) {
  return isActive ? (
    <Badge className="bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400">
      Active
    </Badge>
  ) : (
    <Badge className="bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400">
      Inactive
    </Badge>
  )
}

export default function AdminUsersPage() {
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [actionTarget, setActionTarget] = useState<AdminUserResponse | null>(null)
  const [pendingAction, setPendingAction] = useState<'deactivate' | 'reactivate' | null>(null)

  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()

  const usersQuery = useQuery({
    queryKey: adminKeys.users.list({
      role: roleFilter === 'all' ? undefined : roleFilter,
      is_active: statusFilter === 'all' ? undefined : statusFilter === 'active',
      page,
    }),
    queryFn: () =>
      fetchAdminUsers(accessToken, {
        role: roleFilter === 'all' ? null : roleFilter,
        is_active: statusFilter === 'all' ? null : statusFilter === 'active',
        page,
        per_page: PAGE_SIZE,
      }),
    enabled: !!accessToken,
    staleTime: 30_000,
  })

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateUser(accessToken, actionTarget!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users.all })
      toast.success(`${actionTarget!.email} has been deactivated`)
      setActionTarget(null)
      setPendingAction(null)
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError ? error.detail ?? 'Failed to deactivate user' : 'Failed to deactivate user'
      )
    },
  })

  const reactivateMutation = useMutation({
    mutationFn: () => reactivateUser(accessToken, actionTarget!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users.all })
      toast.success(`${actionTarget!.email} has been reactivated`)
      setActionTarget(null)
      setPendingAction(null)
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError ? error.detail ?? 'Failed to reactivate user' : 'Failed to reactivate user'
      )
    },
  })

  function handleRoleChange(value: string) {
    setRoleFilter(value)
    setPage(1)
  }

  function handleStatusChange(value: string) {
    setStatusFilter(value)
    setPage(1)
  }

  const columns: ColumnDef<AdminUserResponse, unknown>[] = [
    {
      accessorKey: 'email',
      header: 'Email',
      cell: ({ row }) => (
        <span className="font-medium">{row.original.email}</span>
      ),
    },
    {
      id: 'role',
      header: 'Role',
      cell: ({ row }) => <RoleBadge role={row.original.role} />,
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => <ActiveBadge isActive={row.original.is_active} />,
    },
    {
      id: 'joined',
      header: 'Joined',
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {new Date(row.original.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const user = row.original
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {user.is_active === true && (
                <DropdownMenuItem
                  disabled={user.role === 'admin'}
                  className={user.role === 'admin' ? 'cursor-not-allowed opacity-50' : ''}
                  onClick={() => {
                    setActionTarget(user)
                    setPendingAction('deactivate')
                  }}
                >
                  Deactivate
                </DropdownMenuItem>
              )}
              {user.is_active === false && (
                <DropdownMenuItem
                  onClick={() => {
                    setActionTarget(user)
                    setPendingAction('reactivate')
                  }}
                >
                  Reactivate
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )
      },
    },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">User Management</h1>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3">
        <Select value={roleFilter} onValueChange={handleRoleChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All Roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Roles</SelectItem>
            <SelectItem value="user">User</SelectItem>
            <SelectItem value="admin">Admin</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Error state */}
      {usersQuery.isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 flex items-center justify-between">
          <p className="text-sm text-destructive">Failed to load users.</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => usersQuery.refetch()}
          >
            Retry
          </Button>
        </div>
      )}

      {/* Users table */}
      <DataTable
        columns={columns}
        data={usersQuery.data?.items ?? []}
        isLoading={usersQuery.isLoading}
        emptyMessage="No users found."
      />

      {/* Pagination */}
      {(usersQuery.data?.total_count ?? 0) > 0 && (
        <AdminPagination
          page={page}
          total={usersQuery.data?.total_count ?? 0}
          size={PAGE_SIZE}
          onPageChange={setPage}
        />
      )}

      {/* Deactivate / Reactivate confirmation dialog */}
      <ConfirmDialog
        open={actionTarget !== null && pendingAction !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActionTarget(null)
            setPendingAction(null)
          }
        }}
        title={pendingAction === 'deactivate' ? 'Deactivate User' : 'Reactivate User'}
        description={
          pendingAction === 'deactivate'
            ? `This will immediately revoke ${actionTarget?.email}'s session tokens and lock them out. They will not be able to log in until reactivated.`
            : `Restore access for ${actionTarget?.email}? They will be able to log in immediately.`
        }
        confirmLabel={pendingAction === 'deactivate' ? 'Deactivate' : 'Reactivate'}
        onConfirm={() =>
          pendingAction === 'deactivate' ? deactivateMutation.mutate() : reactivateMutation.mutate()
        }
        isPending={deactivateMutation.isPending || reactivateMutation.isPending}
      />
    </div>
  )
}

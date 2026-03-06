import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { notificationsStorage } from '@/lib/notifications/storage';

export async function PUT(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const userId = DEV_USER.id;

  const { id } = await params;
  await notificationsStorage.markAsRead(id, userId);
  return NextResponse.json({ success: true });
}

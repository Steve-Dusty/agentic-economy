import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { notificationsStorage } from '@/lib/notifications/storage';

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const userId = DEV_USER.id;

  const { id } = await params;
  await notificationsStorage.delete(id, userId);
  return NextResponse.json({ success: true });
}

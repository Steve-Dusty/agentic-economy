import { NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { notificationsStorage } from '@/lib/notifications/storage';

export async function PUT() {
  const userId = DEV_USER.id;

  await notificationsStorage.markAllAsRead(userId);
  return NextResponse.json({ success: true });
}

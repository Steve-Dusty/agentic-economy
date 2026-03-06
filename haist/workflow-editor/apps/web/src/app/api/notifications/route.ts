import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { notificationsStorage } from '@/lib/notifications/storage';

export async function GET(req: NextRequest) {
  const userId = DEV_USER.id;

  const url = req.nextUrl;
  const unreadOnly = url.searchParams.get('unreadOnly') === 'true';
  const limit = parseInt(url.searchParams.get('limit') || '20', 10);
  const offset = parseInt(url.searchParams.get('offset') || '0', 10);

  const result = await notificationsStorage.getByUserId(userId, {
    unreadOnly,
    limit,
    offset,
  });

  return NextResponse.json(result);
}

export async function POST(req: NextRequest) {
  const userId = DEV_USER.id;

  const body = await req.json();
  const notification = await notificationsStorage.create({
    userId,
    type: body.type,
    title: body.title,
    body: body.body,
    ruleId: body.ruleId,
    ruleName: body.ruleName,
    logId: body.logId,
  });

  return NextResponse.json(notification, { status: 201 });
}

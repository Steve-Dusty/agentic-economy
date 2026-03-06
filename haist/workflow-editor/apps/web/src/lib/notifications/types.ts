export type NotificationType = 'execution_success' | 'execution_failure' | 'needs_approval' | 'suggestion' | 'info';

export interface Notification {
  id: string;
  userId: string;
  type: NotificationType;
  title: string;
  body: string;
  ruleId?: string;
  ruleName?: string;
  logId?: string;
  read: boolean;
  createdAt: string;
}

export interface NotificationInput {
  userId: string;
  type: NotificationType;
  title: string;
  body: string;
  ruleId?: string;
  ruleName?: string;
  logId?: string;
}

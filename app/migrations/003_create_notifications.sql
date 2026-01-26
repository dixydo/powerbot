-- Create notifications table for logging message send attempts
-- This replaces the previous (unused) migration. We're rewriting migrations as the project is not yet in production.

create table if not exists notifications (
    id bigserial primary key,
    telegram_user_id bigint not null,
    status text not null,
    message text,
    telegram_message_id bigint null,
    error_text text null,
    attempts int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_notifications_telegram_user_id on notifications (telegram_user_id);
create index if not exists idx_notifications_created_at on notifications (created_at desc);

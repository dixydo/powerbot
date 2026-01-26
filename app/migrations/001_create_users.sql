create table if not exists users (
    id bigserial primary key,
    telegram_user_id bigint not null unique,
    username text null,
    first_name text null,
    last_name text null,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_users_is_active on users (is_active);


-- Power state changes (electricity on/off) as observed by the bot.
-- Keep raw API payload for auditing/debugging.

do $$
begin
    create type power_state as enum ('on', 'off');
exception
    when duplicate_object then null;
end $$;

create table if not exists power_events (
    id bigserial primary key,
    state power_state not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_power_events_created_at on power_events (created_at desc);

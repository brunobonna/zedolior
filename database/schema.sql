-- ============================================================
-- Zé do Lior Viagens — Schema Supabase
-- Execute no SQL Editor do Supabase (supabase.com)
-- ============================================================

-- ============================================================
-- TABELAS
-- ============================================================

create table trips (
  id            uuid primary key default gen_random_uuid(),
  origin        text not null,
  destination   text not null,
  departure_at  timestamptz not null,
  arrival_at    timestamptz,
  total_seats   integer not null check (total_seats > 0),
  price         numeric(10, 2) not null check (price >= 0),
  status        text not null default 'active'
                  check (status in ('active', 'cancelled', 'completed')),
  notes         text,         -- observações internas (só no admin)
  public_notes  text,         -- observações públicas (aparece no site)
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create table trip_stops (
  id           uuid primary key default gen_random_uuid(),
  trip_id      uuid not null references trips(id) on delete cascade,
  city         text not null,
  stop_order   integer not null,  -- 0 = origem, crescente, último = destino
  created_at   timestamptz not null default now(),
  unique (trip_id, stop_order),
  unique (trip_id, city)
);

create table passengers (
  id              uuid primary key default gen_random_uuid(),
  trip_id         uuid not null references trips(id) on delete cascade,
  name            text not null,
  cpf             text not null,
  rg              text,
  birth_date      date not null,
  is_minor        boolean not null default false,
  boarding_city   text not null,
  alighting_city  text not null,
  seat_status     text not null default 'reserved'
                    check (seat_status in ('reserved', 'paid')),
  seat_type       text not null default 'poltrona'
                    check (seat_type in ('poltrona', 'colo')),
  notes           text,
  source          text not null default 'admin'
                    check (source in ('admin', 'public_request')),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table pending_requests (
  id              uuid primary key default gen_random_uuid(),
  trip_id         uuid not null references trips(id) on delete cascade,
  boarding_city   text not null,
  alighting_city  text not null,
  passenger_count integer not null check (passenger_count >= 1),
  passengers_json jsonb not null,
  -- Formato esperado:
  -- [{"name": "", "cpf": "", "rg": "", "birth_date": "YYYY-MM-DD", "phone": "", "seat_type": "poltrona|colo"}]
  status          text not null default 'pending'
                    check (status in ('pending', 'approved', 'rejected')),
  rejection_note  text,
  submitted_at    timestamptz not null default now(),
  reviewed_at     timestamptz
);

-- ============================================================
-- TRIGGERS para updated_at
-- ============================================================

create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger trips_updated_at
  before update on trips
  for each row execute procedure set_updated_at();

create trigger passengers_updated_at
  before update on passengers
  for each row execute procedure set_updated_at();

-- ============================================================
-- VIEW: disponibilidade de vagas por viagem
-- ============================================================

create view trip_availability as
select
  t.id,
  t.origin,
  t.destination,
  t.departure_at,
  t.arrival_at,
  t.total_seats,
  t.price,
  t.status,
  t.notes,
  t.public_notes,
  count(p.id) filter (where p.seat_type = 'poltrona') as seats_taken,
  t.total_seats - count(p.id) filter (where p.seat_type = 'poltrona') as seats_available
from trips t
left join passengers p on p.trip_id = t.id
group by t.id;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

alter table trips             enable row level security;
alter table trip_stops        enable row level security;
alter table passengers        enable row level security;
alter table pending_requests  enable row level security;

-- Anônimos podem ler viagens ativas
create policy "public_read_active_trips"
  on trips for select
  to anon
  using (status = 'active');

-- Anônimos podem ler paradas de viagens ativas
create policy "public_read_active_trip_stops"
  on trip_stops for select
  to anon
  using (
    exists (
      select 1 from trips t
      where t.id = trip_stops.trip_id
        and t.status = 'active'
    )
  );

-- Anônimos podem submeter solicitações (sem leitura)
create policy "public_insert_pending_requests"
  on pending_requests for insert
  to anon
  with check (true);

-- passengers: sem acesso público — apenas service_role (bypassa RLS)

-- ============================================================
-- FUNÇÕES PARA TELA DE MONITOR (Everaldo)
-- Security definer: rodam como owner, expõem apenas campos seguros
-- ============================================================

create or replace function get_passengers_for_monitor()
returns table (
  id            uuid,
  trip_id       uuid,
  name          text,
  phone         text,
  seat_status   text,
  seat_type     text,
  boarding_city text,
  alighting_city text,
  group_leader  text
)
security definer
language sql
as $$
  select p.id, p.trip_id, p.name, p.phone, p.seat_status, p.seat_type,
         p.boarding_city, p.alighting_city, p.group_leader
  from passengers p
  join trips t on t.id = p.trip_id
  where t.status = 'active'
  order by p.seat_status, p.created_at;
$$;

create or replace function get_trip_pending_counts()
returns table (
  trip_id              uuid,
  pending_requests_count bigint,
  pending_passengers   bigint
)
security definer
language sql
as $$
  select pr.trip_id, count(*), sum(pr.passenger_count)
  from pending_requests pr
  join trips t on t.id = pr.trip_id
  where t.status = 'active' and pr.status = 'pending'
  group by pr.trip_id;
$$;

grant execute on function get_passengers_for_monitor() to anon;
grant execute on function get_trip_pending_counts() to anon;

-- ============================================================
-- DADOS DE EXEMPLO (opcional — remova se não quiser)
-- ============================================================

-- Descomente para criar uma viagem de teste:
/*
insert into trips (origin, destination, departure_at, arrival_at, total_seats, price)
values ('Rio de Janeiro', 'São Paulo', now() + interval '3 days', now() + interval '3 days 6 hours', 8, 120.00);

insert into trip_stops (trip_id, city, stop_order)
select id, 'Rio de Janeiro', 0 from trips order by created_at desc limit 1;

insert into trip_stops (trip_id, city, stop_order)
select id, 'Volta Redonda', 1 from trips order by created_at desc limit 1;

insert into trip_stops (trip_id, city, stop_order)
select id, 'São Paulo', 2 from trips order by created_at desc limit 1;
*/

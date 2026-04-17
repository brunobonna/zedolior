-- ============================================================
-- Migration 001 — seat_type + funções de monitor
-- Execute no SQL Editor do Supabase (supabase.com)
-- ============================================================

-- 1. Adiciona coluna seat_type na tabela passengers
alter table passengers
  add column if not exists seat_type text not null default 'poltrona'
    check (seat_type in ('poltrona', 'colo'));

-- 2. Recria a view trip_availability para excluir passageiros "colo" da contagem de vagas
create or replace view trip_availability as
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

-- 3. Função para a tela de monitor — retorna passageiros sem CPF/RG
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

-- 4. Função para contar pendentes por viagem (sem expor dados dos passageiros)
create or replace function get_trip_pending_counts()
returns table (
  trip_id                uuid,
  pending_requests_count bigint,
  pending_passengers     bigint
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

-- 5. Permite que o site público (chave anon) chame as funções do monitor
grant execute on function get_passengers_for_monitor() to anon;
grant execute on function get_trip_pending_counts() to anon;

-- ============================================================
-- Migration 002 — Verificação de senha do monitor via Supabase
-- Execute no SQL Editor do Supabase (supabase.com)
--
-- ATENÇÃO: Substitua 'SUA_SENHA_AQUI' pela senha real
--          antes de rodar. Não salve a senha real neste arquivo.
-- ============================================================

create or replace function check_monitor_access(pwd text)
returns boolean
security definer
language plpgsql
as $$
begin
  return lower(trim(pwd)) = 'SUA_SENHA_AQUI';
end;
$$;

grant execute on function check_monitor_access(text) to anon;

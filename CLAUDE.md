# Zé do Lior Viagens — Referência do Projeto

## O que é

Sistema de gestão de transporte rodoviário de passageiros para a empresa **Zé do Lior Viagens**, de Everaldo (sogro do Bruno, o dev). Permite que clientes vejam viagens disponíveis e solicitem reservas via WhatsApp, enquanto o admin gerencia viagens, passageiros e solicitações pendentes.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Banco de dados | Supabase (PostgreSQL) |
| Admin | Streamlit (Python) |
| Site público | HTML5 + CSS3 + JavaScript vanilla |
| Deploy admin | Streamlit Cloud |
| Deploy público | GitHub Pages (`/docs`) |

---

## Estrutura de pastas

```
zedolior/
├── database/
│   ├── schema.sql                          # DDL completo: tabelas, views, RLS, funções
│   └── migrations/
│       ├── 001_seat_type_and_monitor.sql   # seat_type, view atualizada, funções RPC monitor
│       └── 002_monitor_password.sql        # check_monitor_access (template — senha não commitada)
├── admin/
│   ├── app.py              # Entry point: autenticação + navegação
│   ├── app_painel.py       # Página Painel (📊)
│   ├── config.py           # Supabase client + leitura de secrets
│   ├── requirements.txt    # streamlit, supabase, pandas, python-dateutil
│   ├── .streamlit/
│   │   └── secrets.toml    # NÃO commitado — ver seção Secrets
│   └── pages/
│       ├── 1_Viagens.py    # CRUD de viagens + paradas + exportação para empresa
│       ├── 2_Passageiros.py# Gestão de passageiros por viagem
│       └── 3_Pendentes.py  # Revisão de solicitações do site público
└── docs/
    ├── index.html          # Estrutura + configuração JS (SUPABASE_URL etc.)
    ├── app.js              # Lógica: lista viagens, formulário, WhatsApp
    ├── style.css           # CSS com custom properties (--brand, --accent)
    ├── monitor.html        # Tela somente-leitura para acompanhamento (senha via Supabase)
    ├── monitor.js          # Lógica do monitor: login RPC, dashboard, cards de viagem
    └── manual.html         # Manual do operador (mobile-first, sem nomes de pessoas)
```

---

## Banco de dados

### Tabelas principais

**`trips`** — viagens/rotas
- `id`, `origin`, `destination`, `departure_at`, `arrival_at`
- `total_seats`, `price`, `status` (`active` | `cancelled` | `completed`)
- `notes` (admin only), `public_notes` (visível no site)

**`trip_stops`** — paradas intermediárias
- `trip_id`, `city`, `stop_order` (0 = origem, último = destino)
- Unique: `(trip_id, stop_order)`, `(trip_id, city)`

**`passengers`** — passageiros confirmados
- `trip_id`, `name`, `cpf`, `rg`, `birth_date`, `is_minor`
- `boarding_city`, `alighting_city`
- `seat_status`: `reserved` | `paid`
- `seat_type`: `poltrona` | `colo` (colo = menor de 7 anos no colo do acompanhante, não ocupa vaga)
- `phone`, `group_leader`, `notes`
- `source`: `admin` | `public_request`

**`pending_requests`** — solicitações do site público
- `trip_id`, `boarding_city`, `alighting_city`, `passenger_count`
- `passengers_json` (jsonb): array com name, cpf, rg, birth_date, phone, seat_type, notes
- `status`: `pending` | `approved` | `rejected`
- `rejection_note`

### View

**`trip_availability`** — trips ativas + `seats_taken` (só poltrona) + `seats_available`

### Funções RPC (security definer)

**`get_passengers_for_monitor()`** — retorna passageiros de viagens ativas sem CPF/RG (seguro para anon key)

**`get_trip_pending_counts()`** — retorna contagem de pendentes por trip_id para anon key

**`check_monitor_access(pwd text)`** — verifica senha do monitor; senha real configurada no Supabase, nunca no código

### RLS (Row-Level Security)
- Anon: lê apenas viagens/paradas ativas, insere pending_requests, executa funções RPC do monitor
- Service role (admin): acesso total, bypass RLS

---

## Admin (Streamlit)

Autenticação por senha (secrets.toml `ADMIN_PASSWORD`). Quatro seções:

| Página | Arquivo | Funcionalidades |
|---|---|---|
| 📊 Painel | app_painel.py | Métricas rápidas, lista de viagens ativas com contagens |
| 🗺️ Viagens | pages/1_Viagens.py | CRUD viagens, editor dinâmico de paradas, cancelar/concluir |
| 👥 Passageiros | pages/2_Passageiros.py | Listar/adicionar/editar/remover pax, trocar status, WhatsApp |
| 📬 Pendentes | pages/3_Pendentes.py | Aprovar/rejeitar solicitações do site, editar dados antes de aprovar |

---

## Site público (`docs/`)

- Lista viagens da view `trip_availability` + paradas de `trip_stops`
- Formulário de reserva: embarcamento, desembarcamento, N passageiros
- Submissão: abre WhatsApp com mensagem pré-preenchida + insere em `pending_requests`
- Configuração em `index.html` (3 variáveis globais):
  ```js
  window.SUPABASE_URL    = "https://rrwgwxylgbkdcwdpkbxw.supabase.co";
  window.SUPABASE_ANON_KEY = "eyJ...";
  window.WHATSAPP_NUMBER = "5521981695585";
  ```

---

## Secrets

Arquivo `admin/.streamlit/secrets.toml` (NÃO commitado):

```toml
SUPABASE_URL      = "https://rrwgwxylgbkdcwdpkbxw.supabase.co"
SUPABASE_SERVICE_KEY = "eyJ..."   # service_role — nunca expor
ADMIN_PASSWORD    = "Sucesso2026!"
WHATSAPP_NUMBER   = "5521981695585"
```

No Streamlit Cloud: cole o conteúdo em **Advanced settings → Secrets**.

---

## Como rodar localmente

```bash
cd admin
pip install -r requirements.txt
# garantir que .streamlit/secrets.toml existe
streamlit run app.py
```

Site público: abrir `docs/index.html` direto no navegador ou servir com qualquer servidor estático.

---

## Decisões arquiteturais

- **Sem framework no frontend**: site público é HTML/JS vanilla para facilitar deploy no GitHub Pages sem build step.
- **Streamlit para admin**: rápido de desenvolver em Python, deploy gratuito no Streamlit Cloud.
- **WhatsApp como canal primário**: o cliente envia mensagem diretamente ao dono. O `pending_requests` é backup/registro — não é o canal principal de comunicação.
- **`source` no passenger**: distingue quem veio do site (`public_request`) de quem foi adicionado manualmente pelo admin (`admin`).
- **RLS no Supabase**: anon key é seguro no frontend porque as policies impedem leitura/escrita não autorizada.
- **`docs/` como pasta do GitHub Pages**: padrão do GitHub Pages para sites sem Jekyll.
- **`group_leader`**: responsável pelo grupo quando vários passageiros viajam juntos; campo livre (nome da pessoa).
- **`seat_type` / colo**: menores de 7 anos podem ir no colo do acompanhante (`seat_type = 'colo'`); não contam como vaga ocupada na view nem nas métricas do admin.
- **Monitor somente-leitura**: `docs/monitor.html` + `docs/monitor.js`; senha verificada via RPC `check_monitor_access()` — nunca exposta no código-fonte. Usa `sessionStorage` para persistir login.
- **Funções RPC como camada de segurança**: `get_passengers_for_monitor()` e `get_trip_pending_counts()` rodam como security definer, expondo apenas campos seguros à anon key sem precisar relaxar RLS nas tabelas.
- **Manual do operador**: `docs/manual.html` — página mobile-first sem dependências externas, explica os dois perfis de uso (monitor e admin) e o fluxo do dia a dia.

# Changelog — Zé do Lior Viagens

## v1.0 — Vagas por label, colo, monitor Everaldo e exportação
**Data:** 2026-04-17

- **Vagas no site:** em vez de número, exibe "Mais de 10 vagas" / "Poucas vagas" / "Últimas vagas"
- **Opção colo:** passageiros menores de 7 anos podem escolher Poltrona ou Colo do acompanhante; colo não ocupa vaga no ônibus (banco, admin e site)
- **Monitor do Everaldo** (`docs/monitor.html`): tela de acompanhamento com senha "perola", mostra viagens ativas com contagem de pagos/reservados/pendentes; ao clicar nos nomes abre dados com botão WhatsApp
- **Exportação para empresa** (Admin → Viagens): botão "📋 Lista para empresa de ônibus" gera texto copiável com dados da viagem e lista de passageiros confirmados
- **Migration SQL** em `database/migrations/001_seat_type_and_monitor.sql` — precisa ser rodado no Supabase antes de usar

---


Histórico de versões e avanços funcionais do sistema.

---

## v0.9 — Group leader e formato de data de nascimento
**Commit:** `87a3542`

- Data de nascimento exibida em DD/MM/YYYY no admin e na mensagem WhatsApp
- Campo `group_leader` para identificar o responsável de grupos de passageiros

---

## v0.8 — Telefone por passageiro
**Commit:** `f436a88`

- Campo de telefone individual por passageiro no formulário público
- Telefone incluído na mensagem WhatsApp enviada ao admin
- Campo `phone` adicionado ao banco de dados (`passengers` e `passengers_json`)
- Botão de WhatsApp individual por passageiro no painel admin

---

## v0.7 — Quatro melhorias de usabilidade
**Commit:** `d287e62`

- Telefone no formulário público (versão inicial)
- Botão para cancelar viagem direto no painel admin
- Contador de vagas disponíveis visível no painel
- Layout mobile melhorado com ícones

---

## v0.6 — Sete correções
**Commit:** `7b0c32c`

- Aba Pendentes mostra apenas solicitações de viagens ativas
- Opção "Avaliar depois" na revisão de pendentes
- Contagem de reservados visível no painel
- Fluxo de conclusão de viagem corrigido
- Observações exibidas abaixo da lista de passageiros
- Resumo da viagem no card
- Métricas de passageiros corrigidas

---

## v0.5 — Seis melhorias de fluxo
**Commit:** `d959642`

- Pendentes filtrados para mostrar apenas viagens ativas
- Confirmação antes de concluir viagem
- Status do passageiro auto-salva (sem botão explícito)
- Item "Painel" adicionado ao menu de navegação
- Lista de passageiros visível diretamente no card da viagem
- Observação pública incluída na view `trip_availability`

---

## v0.4 — Fix WhatsApp mobile
**Commit:** `f7dd4e6`

- Correção crítica: no mobile, `window.open` era bloqueado por pop-up blockers se chamado após `await`
- Solução: redirecionamento via `window.location.href` executado antes do `await` do fetch ao banco

---

## v0.3 — Nove melhorias gerais
**Commit:** `7ca7107`

- Painel reformulado com métricas
- Confirmação ao cancelar viagem
- Editor de paradas intermediárias dinâmico
- Botão de recarregar viagens no site público
- Campo de observação pública na viagem
- Outras melhorias menores de UX

---

## v0.2 — Melhorias no formulário e pendentes
**Commit:** `cb65b81`

- Melhorias no formulário de criação de viagens
- Melhorias na tela de pendentes (aprovação e rejeição)

---

## v0.1 — Estrutura inicial
**Commits:** `8af6a83`, `07ce567`, `a261a23`

- Estrutura base do projeto (database, admin, docs)
- Schema do banco: `trips`, `trip_stops`, `passengers`, `pending_requests`, view `trip_availability`
- RLS: leitura pública de viagens ativas, inserção de pending_requests
- Admin Streamlit com autenticação por senha
- Páginas: Viagens, Passageiros, Pendentes
- Site público: listagem de viagens + formulário de reserva + integração WhatsApp
- Renomeação de `public/` para `docs/` (padrão GitHub Pages)

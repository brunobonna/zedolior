# Zé do Lior Viagens

Sistema de gestão de transporte de passageiros entre cidades.

## Estrutura

```
zedolior/
├── database/schema.sql   → Execute no Supabase para criar as tabelas
├── admin/                → Painel administrativo (Streamlit/Python)
└── public/               → Site público (HTML/CSS/JS)
```

## Configuração inicial

### 1. Supabase (banco de dados)

1. Crie uma conta gratuita em [supabase.com](https://supabase.com)
2. Crie um novo projeto
3. Vá em **SQL Editor** e execute o conteúdo de `database/schema.sql`
4. Anote as chaves em **Settings → API**:
   - **Project URL**
   - **anon / public** (para o site público)
   - **service_role / secret** (para o admin — nunca expor)

### 2. Admin (Streamlit)

**Rodando localmente:**

```bash
cd admin
pip install -r requirements.txt
# Edite .streamlit/secrets.toml com suas credenciais
streamlit run app.py
```

**Publicando no Streamlit Cloud:**

1. Faça push do projeto para um repositório GitHub (privado recomendado)
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte o repositório
3. Arquivo principal: `admin/app.py`
4. Em **Advanced settings → Secrets**, copie o conteúdo do `secrets.toml`

### 3. Site público

**Configuração:**

Edite as 3 linhas no final de `public/index.html`:

```javascript
window.SUPABASE_URL    = "https://SEU-PROJETO.supabase.co";
window.SUPABASE_ANON_KEY = "eyJ...";   // chave anon/public
window.WHATSAPP_NUMBER = "5521981695585";
```

**Publicando no GitHub Pages:**

1. No repositório GitHub, vá em **Settings → Pages**
2. Source: branch `main`, pasta `/public`
3. O site ficará disponível em `https://seu-usuario.github.io/seu-repositorio/`

Ou arraste a pasta `public/` para [netlify.com/drop](https://netlify.com/drop) para um deploy instantâneo.

## Uso do painel admin

- **Viagens**: cadastre rotas com cidades de parada, datas, vagas e preço
- **Passageiros**: gerencie quem está em cada viagem e o status de pagamento
- **Pendentes**: veja e aprove solicitações que vieram pelo site público

## Fluxo de reserva

1. Cliente acessa o site → vê as viagens disponíveis
2. Clica em "Reservar" → preenche seus dados no formulário
3. Clica em "Confirmar" → WhatsApp abre com mensagem pré-preenchida
4. Admin conversa com o cliente, confirma pagamento fora do sistema
5. Admin aprova a solicitação no painel (aba Pendentes) e adiciona o passageiro

# Early Childhood Coach

## O que estamos construindo

Dispositivo wearable + app que ajuda pais a ter mais "conversational turns" com filhos de 0-6 anos. Baseado na ciencia do Center on Developing Child (Harvard): interacoes serve-and-return constroem o cerebro da crianca.

O dispositivo escuta conversas, detecta momentos de conexao verbal, e da feedback POSITIVO e gentil. Nunca julga, nunca pune.

## Problema que resolvemos

Criancas de familias menos privilegiadas chegam aos 3 anos tendo ouvido ate 30 milhoes de palavras a menos. Pais nao sabem da importancia dessa fase. Queremos mudar isso de forma acessivel e nao-invasiva.

## Filosofia do produto (CRITICO)

- Produto e um COACH GENTIL, nao um juiz
- Foco em CELEBRAR ACERTOS, nao apontar erros
- Aceita que audio so captura PARTE da interacao (olhares, toques nao sao medidos)
- Tom sempre ESPERANCOSO e ENCORAJADOR
- Reconhecer o que pais JA FAZEM BEM antes de sugerir algo novo
- Pequenos passos incrementais, nunca sobrecarregar

## Os 5 passos de serve-and-return

1. Share focus - seguir interesse da crianca
2. Support - encorajar com expressoes, olhar, toque
3. Name it - narrar o que estao fazendo (constroi vocabulario)
4. Take turns - paciencia, deixar crianca desenvolver
5. Practice endings - ajudar nas transicoes entre atividades

Audio so detecta passos 3 e 4. Isso e OK - somos honestos sobre a limitacao.

## Stack tecnica

- **Deteccao de fala:** WebRTC VAD (158 KB, leve, funciona offline)
- **Classificacao adulto/crianca:** Analise de pitch com YIN algorithm (adulto <280Hz, crianca >=280Hz)
- **Hardware prototipo:** Raspberry Pi Zero 2 W (Python)
- **Hardware producao:** ESP32-S3 (C++)
- **Backend:** Supabase (free tier, opcional)
- **App:** Lovable (conecta via API REST)
- **Dataset de referencia:** Playlogue (14.111 conversational turns analisados)

## Status atual

- ✅ VAD funcionando e testado
- ✅ Deteccao de pitch funcionando (YIN algorithm)
- ✅ Dataset Playlogue analisado (baseline: 93.5% taxa resposta, <1s tempo medio)
- ✅ API REST completa com Flask + CORS
- ✅ App Lovable criado (com dados mock)
- ✅ Conteudo educacional (dicas semanais dos 5 passos)
- ✅ Persistencia offline (JSON local com auto-save)
- ✅ Resumo semanal com tendencias e dicas
- 🔄 Testar no PC com microfone (resolver permissoes Windows)
- 📋 Conectar Lovable com API real
- 📋 Comprar Pi Zero 2 W para prototipo

## Parametros de deteccao

- Janela de resposta: 15 segundos (generoso, nao punitivo)
- Duracao minima de fala: 0.5 segundos
- Confianca minima de pitch: 85%
- Ignorar sons muito curtos: <0.3 segundos
- Pitch crianca: >= 280Hz
- VAD agressividade: 2 (de 0-3)

## Feedback em tempo real

- ✅ Luz verde suave (2s) quando detecta momento de conversa
- ❌ NENHUMA vibracao
- ❌ NENHUM alerta de "missed opportunity"
- Opcional: botao "respondi" para respostas nao-verbais

## Resumo semanal (nao diario)

Retorna:
- moments: total de momentos de conversa
- trend: "up", "down", "stable"
- tip: UMA dica da semana (rotaciona entre os 5 passos)
- encouragement: frase positiva

## Tom e linguagem (CRITICO)

NUNCA usar:
- "perdeu"
- "falhou"
- "errou"
- "missed"
- "oportunidade perdida"

SEMPRE usar:
- "momento"
- "conexao"
- "conversa"
- "progresso"

## Endpoints da API

```
GET  /api/status   - {listening, current_speaker, current_pitch, seconds_since_last_speech}
GET  /api/session  - {session_id, moments, child_speech, adult_speech, moments_per_hour, events}
GET  /api/weekly   - {moments, trend, tip, encouragement}
GET  /api/summary  - sessao atual + resumo semanal (?weekly=true)
GET  /api/sessions - historico de sessoes salvas
POST /api/start    - inicia sessao
POST /api/stop     - para e salva sessao
POST /api/save     - forca salvamento da sessao ativa
POST /api/sync     - sincroniza com Supabase (opcional)
```

## Requisitos de funcionamento

- 100% offline (nao depende de WiFi)
- Funciona outdoor
- Sem dependencia de app aberto
- Pai controla quando liga/desliga
- Bateria >8 horas

## O que NAO fazer

- ❌ Treinar LLM proprio (usar API, muito caro)
- ❌ Monitorar stress/heart rate (outro produto, regulamentacao pesada)
- ❌ Analisar exames medicos (FDA/ANVISA)
- ❌ Ativacao automatica por proximidade (complexidade desnecessaria no MVP)
- ❌ Feedback negativo em tempo real
- ❌ Over-engineering: cada feature precisa justificar sua existencia

## Arquivos importantes

- `/algorithm/realtime_detector.py` - Detector principal com API Flask
- `/algorithm/content/weekly_tips.json` - Dicas semanais dos 5 passos
- `/algorithm/data/sessions/` - Sessoes salvas localmente (JSON)

## Contexto do fundador

Victor esta fazendo transicao de M&A law para early childhood education. Esta no board do IVAS (pre-escola com 90 criancas em Orlandia, SP). Preparando para MBA em HBS/Stanford GSB. Foco em resolver problema real de forma acessivel.

## Principio guia

"Idiot index" e Musk algorithm: questionar cada requisito. Cada feature precisa justificar sua existencia. Simplicidade > complexidade. Acessibilidade > perfeicao.

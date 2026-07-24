# AUDITORIA DE PROCEDIMENTOS — CHECKLISTS DE CONFORMIDADE

Use quando o usuário pedir para **analisar, revisar, auditar ou verificar erros** em um processo/procedimento existente. Objetivo: atuar como auxiliar de análise de conformidade (assessoria jurídica / Corregedoria).

## MÉTODO DE AUDITORIA (sempre nesta ordem)

1. **Identificar o tipo de processo** (PCD, SAD, PAD, PADS, PAE, RIP, PR, sindicância de viatura) e ler o capítulo correspondente em `references/`.
2. **Montar a linha do tempo**: extrair TODAS as datas (portaria, recibo, notificações, oitivas, TAV, RED, relatório, remessa, CEDMU, solução) e conferir cada prazo contra `tabela-prazos-consolidada.md`.
3. **Verificar competência e legitimidade**: autoridade instauradora (art. 45 CEDM), precedência hierárquica do encarregado/sindicante, impedimento/suspeição.
4. **Conferir a sequência do rito** contra o checklist do processo: peça ausente, fora de ordem, ou dispensada indevidamente.
5. **Auditar cada notificação**: antecedência (24h/48h), forma, ciente/termo de recusa, registro nos autos.
6. **Auditar o contraditório**: defesa notificada de TODOS os atos? Perguntas da defesa registradas? Novo TAV após diligência nova?
7. **Auditar o relatório** (seção própria abaixo).
8. **Verificar formalidades**: numeração/rubrica de folhas, ordem cronológica, espaços em branco cancelados, 1 via, termos de juntada corretos.
9. **Verificar prescrição** (cap16): interrupções, suspensões, prazos do art. 66 CEDM.
10. **Emitir parecer** classificando cada achado (ver `matriz-erros-nulidades.md`): NULIDADE ABSOLUTA / NULIDADE RELATIVA / IRREGULARIDADE FORMAL / VÍCIO DE MÉRITO / RECOMENDAÇÃO.

## FORMATO DO PARECER DE AUDITORIA

```
PARECER DE ANÁLISE DE CONFORMIDADE — [TIPO] nº [número]
1. IDENTIFICAÇÃO (processo, sindicado, sindicante, unidade, datas-chave)
2. LINHA DO TEMPO E PRAZOS (tabela: ato → data → prazo legal → situação ✅/⚠️/❌)
3. ACHADOS (numerados: descrição + base legal violada + classificação + consequência + como sanear)
4. DILIGÊNCIAS FALTANTES (o que deveria constar e não consta)
5. ANÁLISE DO RELATÓRIO
6. CONCLUSÃO (apto a prosseguir / devolver para saneamento / risco de nulidade / prescrição)
```

---

## CHECKLIST — SAD (Cap. VIII, arts. 272–320)

| # | Item de verificação | Base legal | Erro típico |
|---|---|---|---|
| 1 | Portaria identifica nominalmente o(s) sindicado(s) | art. 277 | SAD sem sindicado = deveria ser RIP |
| 2 | Fato relatado com verbos/expressões do CEDM + tipificação em tese | art. 277 | Relato genérico sem tipificação |
| 3 | Portaria publicada em BI (sigilosa → boletim sigiloso) | art. 281 | Sem publicação |
| 4 | Sindicante: Of/Subten/Sgt com precedência sobre o sindicado | art. 283 | Sindicante mais moderno |
| 5 | Sindicante sem impedimento/suspeição | art. 284 | Comunicante atuando como sindicante |
| 6 | Recibo da portaria pelo sindicante (marco do prazo) | art. 274 | Sem data de recibo |
| 7 | Prazo 30 dias corridos do 1º d.u. após recibo (+10) | arts. 273-274 | Estouro sem prorrogação formal |
| 8 | Prorrogação/sobrestamento motivados e nos autos | art. 273 | Prorrogação verbal/ausente |
| 9 | Autuação: portaria + docs de origem, capa, fl. 01 | art. 287, I | Documentos de origem ausentes |
| 10 | Notificação p/ defesa prévia com libelo (acusação clara) | art. 291 | Libelo sem tipificação |
| 11 | Prazo defesa prévia 2 d.u.; sem oitivas nesse período | art. 291 | Oitiva durante prazo de defesa prévia |
| 12 | Interrogatório = 1ª pessoa ouvida (salvo justificativa) | arts. 126, 293 | Testemunhas antes do interrogatório |
| 13 | Notificação do interrogatório: mínimo 48h | art. 130 §3º | Notificação em cima da hora |
| 14 | Interrogatório em 2 partes (pessoa + 8 quesitos) | art. 127 | Termo sem qualificação/quesitos |
| 15 | Silêncio do sindicado: perguntas registradas | art. 127 §7º | Termo sem registro das perguntas |
| 16 | Vítima ouvida após interrogatório; sem compromisso | arts. 132-133 | Vítima com compromisso deferido |
| 17 | Notificação da defesa 24h antes de cada ato | arts. 135, 159, 290 | Ato sem notificação = cerceamento |
| 18 | Testemunhas: processo antes da defesa; até 3+3; separadas | arts. 150-151, 287 | Testemunhas ouvidas juntas |
| 19 | Compromisso correto (parentes/menores/deficientes → informantes) | arts. 138, 140 | Parente compromissado |
| 20 | Termos rubricados em todas as folhas, assinados na última | art. 157 | Folhas sem rubrica |
| 21 | TAV p/ RED se persistem indícios (art+inciso+conduta; tipo em branco → norma complementadora) | arts. 302, 304 | TAV sem especificar a conduta |
| 22 | Prazo RED 5 d.u. (10 se +1 sindicado); não computado | art. 303 | Prazo menor concedido |
| 23 | Revelia na RED → oportunizar constituição → Termo Recusa (2 test.) → ad hoc | arts. 306, 309 | Ad hoc sem oportunizar constituição |
| 24 | Defensor: militar com precedência OU advogado; civil não advogado vedado | art. 303 §§3-4 | Defensor sem legitimidade |
| 25 | Diligência/juntada após RED → NOVO TAV + nova RED | art. 305 | Doc juntado após RED sem novo TAV |
| 26 | Relatório: privativo, síntese, analisa cada ponto da defesa, fundamentado | art. 315 | Ver "Auditoria do Relatório" |
| 27 | Crime militar aflorado → solução imediata + IPM | art. 315 §4º | SAD prosseguiu apurando crime |
| 28 | Autos ao CEDMU só após RED juntada; CEDMU 10 d.u.; solução 10 d.u. | arts. 316-317, 520 §5º | CEDMU antes da RED |
| 29 | Sanção publicada em BI Reservado | art. 319 p.u. | Publicação ostensiva sem recomendação |
| 30 | Prescrição verificada (art. 66 CEDM) | cap16 | Punição após prescrição |

## CHECKLIST — PCD (Cap. III)
1. CD com relato objetivo, comunicante identificado, fato datado.
2. Despacho de instauração por autoridade competente delegando a encarregado com precedência.
3. TAV inicial para alegações de defesa — 5 d.u. (art. 37, I).
4. Notificação do comunicado 24h antes de cada ato.
5. Oitivas conforme Cap. VI.
6. TAV final para RED — 5 d.u.
7. Relatório com parecer (existência/inexistência + enquadramento ou arquivamento).
8. Remessa → CEDMU (se houve RED) → solução.
9. Prazo total: 15 + 10 dias.

## CHECKLIST — PAD (Cap. X)
1. Portaria com CPAD (3 oficiais; presidente com precedência sobre o acusado).
2. Notificação do acusado 48h antes da 1ª reunião (art. 336, I).
3. Reunião de instalação; interrogatório.
4. TAV Defesa Prévia — 5 d.u. (art. 345).
5. Testemunhas: máx. 5 por fato; notificações 48h (ou intimação em reunião anterior + 24h de interstício).
6. Gravação audiovisual das oitivas (não das reuniões de instalação/deliberação).
7. TAV RED final — 5 d.u. (art. 355).
8. Reunião de deliberação; relatório da comissão; CEDMU; solução.
9. Prazo: 40 + 20 dias.

## CHECKLIST — PADS (Cap. XI)
Rito do PAD simplificado: autoridade processante singular; prazo 20+10; interrogatório com 48h; ERF antes da RED; CEDMU.

## CHECKLIST — PAE (Cap. XII)
Prazo 30+10; notificação 48h; ERF obrigatório antes da RED (processo exoneratório); TAV defesa 5 d.u.; relatório; solução (arquivamento/exoneração/ação disciplinar).

## CHECKLIST — RIP (Cap. V)
Investigatório — SEM acusado formal, SEM defesa obrigatória, SEM CEDMU. Erro clássico: transformar RIP em acusatório (colher "defesa prévia" de investigado). Prazo 15+10. Conclusão: arquivamento ou proposta de instauração de processo.

---

## AUDITORIA DO RELATÓRIO (qualquer processo)
1. **Autoria**: elaborado pelo titular (sindicante/encarregado/comissão)? Auxiliar não pode (ato privativo).
2. **Estrutura** (art. 315): preâmbulo, diligências, pessoas ouvidas, análise das provas, análise da defesa, dia/hora/local do fato, conclusão.
3. **Vedação de "Ctrl+C"**: reprodução contínua de depoimentos = irregular (art. 315 §1º). Exigir síntese.
4. **Análise da defesa ponto a ponto**: cada argumento das RED enfrentado com motivação (art. 315 §2º)? Argumento ignorado = vício de fundamentação.
5. **Congruência**: conclusão decorre das provas citadas? Enquadramento corresponde ao fato provado.
6. **Conclusão válida** (art. 315 §3º): enquadramento / arquivamento (justificação/absolvição arts. 6º-7º) / remessa MP-PGJ / IPM / PAD-PADS-PAE / outras providências.
7. **Coerência de datas**: relatório posterior à RED (ou à decisão fundamentada de não abrir TAV).
8. **Dosimetria** fundamentada (natureza, gravidade, antecedentes — ERF quando cabível).

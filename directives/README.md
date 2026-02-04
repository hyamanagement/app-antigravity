# Directives

Questa cartella contiene le **SOP (Standard Operating Procedures)** scritte in Markdown.

## Scopo

Le direttive definiscono:
- **Obiettivi**: cosa deve essere raggiunto
- **Input**: dati necessari per l'esecuzione
- **Tool/Script**: quali script in `execution/` utilizzare
- **Output**: risultati attesi
- **Casi limite**: situazioni particolari da gestire

## Come creare una nuova direttiva

1. Crea un file `.md` con un nome descrittivo (es: `scrape_website.md`)
2. Definisci chiaramente obiettivo, input, output e passi
3. Elenca gli script di esecuzione da utilizzare
4. Documenta i casi limite noti

## Esempio di struttura

```markdown
# Nome Direttiva

## Obiettivo
Descrizione di cosa fare

## Input
- parametro1: descrizione
- parametro2: descrizione

## Script di Esecuzione
- `execution/nome_script.py`

## Output
Descrizione del risultato atteso

## Casi Limite
- Caso 1: come gestirlo
- Caso 2: come gestirlo
```

Le direttive sono documenti vivi: aggiornale quando scopri nuovi vincoli o approcci migliori.

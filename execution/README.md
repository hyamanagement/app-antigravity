# Execution Scripts

Questa cartella contiene gli **script Python deterministici** che eseguono il lavoro effettivo.

## Scopo

Gli script di esecuzione:
- Gestiscono chiamate API
- Elaborano dati
- Eseguono operazioni su file
- Interagiscono con database
- Sono affidabili, testabili e veloci

## Linee guida

1. **Commenta bene**: ogni script deve essere ben documentato
2. **Gestisci gli errori**: includi try/except appropriati
3. **Usa .env**: le credenziali vengono da variabili d'ambiente
4. **Testa prima di usare**: verifica che lo script funzioni

## Struttura consigliata

```python
#!/usr/bin/env python3
"""
Nome Script: descrizione breve

Scopo:
    Descrizione dettagliata di cosa fa lo script

Uso:
    python nome_script.py [argomenti]

Input:
    - arg1: descrizione
    - arg2: descrizione

Output:
    Descrizione dell'output
"""

import os
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

def main():
    # Logica principale
    pass

if __name__ == "__main__":
    main()
```

## Dipendenze comuni

Gli script potrebbero richiedere:
- `python-dotenv` - per caricare .env
- `requests` - per chiamate HTTP
- `google-auth` - per API Google

Installa con: `pip install python-dotenv requests`

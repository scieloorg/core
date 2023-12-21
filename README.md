# Core

Usa como base de código: [Template SciELO](https://github.com/scieloorg/template-scms).
Consulte seu [README.md](https://github.com/scieloorg/template-scms/blob/main/README.md).

# Para uso em ambiente de desenvolvimento

## Comandos

Estes comandos são atalhos no desenvolvimento. Não estarão disponíveis em produção.

Eles devem ser configurados como tasks na área administrativa.


1. Inicialização do sistema
```console
python manage.py runscript start --script-args adm
```

2. Coleta de dados de periódicos
```console
python manage.py runscript harvest_am_journal --script-args adm mex
```

3. Carga inicial de dados de periódicos
```console
python manage.py runscript load_journal_from_am_journal --script-args adm mex
```

4. Atribuição de PID para os artigos da coleção scl
```console
python manage.py runscript provide_pid_for_opac_xmls --script-args adm
```

5. Atribuição de PID para os artigos da coleções usando como fonte AM
```console
python manage.py runscript provide_pid_for_am_xmls --script-args adm '["mex", "chl"]'
```

6. Nova tentativa para as falhas de atribuição de PID para os artigos
```console
python manage.py runscript retry_to_provide_pid_for_failed_uris --script-args adm
```

7. Carga de artigos
```console
python manage.py runscript load_articles --script-args 1
```

## Ordem de execução

1 -> 2 -> 3

1 -> 4 -> 5 -> 7

---
name: testes-automatizados
description: Use ao criar testes para validar regras de negócio e segurança do sistema.
---

# Padrões de Teste

## Estrutura
- Testes unitários: funções isoladas (cálculos financeiros, validações)
- Testes de integração: fluxos de API (matrícula, pagamento)
- Testes E2E: fluxos críticos (cadastro → matrícula → cobrança)

## Nomenclatura (Português)
- `deve_rejeitar_aluno_menor_sem_responsavel()`
- `deve_limitar_capacidade_turma_a_9_alunos()`
- `deve_aceitar_pix_cartao_boleto_dinheiro()`
- `deve_calcular_multa_conforme_contrato()`

## Casos de Teste Obrigatórios

### Cadastro
```python
# Regra: Um aluno só pode ter UM responsável
def deve_rejeitar_segundo_responsavel_para_aluno():
    # setup: aluno já tem responsável
    # action: tentar adicionar segundo
    # assert: operação rejeitada com erro claro
```

### Capacidade
```python
# Regra: Capacidade máxima 9 por sala
def deve_rejeitar_decimo_aluno_em_turma():
    # setup: turma com 9 alunos
    # action: matricular 10º
    # assert: matrícula rejeitada
```

### Financeiro
```python
# Regra: PIX, Cartão, Boleto, Dinheiro são válidos
def deve_aceitar_todas_formas_pagamento():
    formas = ["pix", "cartao", "boleto", "dinheiro"]
    for forma in formas:
        assert processar_pagamento(forma) == True
```

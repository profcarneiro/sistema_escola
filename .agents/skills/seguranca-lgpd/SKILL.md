---
name: seguranca-lgpd
description: Use ao revisar código que lida com dados pessoais, especialmente de menores de idade.
---

# Requisitos de Segurança e LGPD

## Dados Sensíveis no Sistema
- CPF de responsáveis
- Endereço residencial
- Telefone/e-mail de responsáveis
- Dados de alunos menores (autorização de imagem, saúde, alergias, medicações)
- Informações financeiras

## Obrigações LGPD
1. **Consentimento explícito** para coleta de dados de menores
2. **Autorização de imagem** separada e registrada
3. **Direito ao esquecimento** — capacidade de excluir dados
4. **Retenção limitada** — não manter dados além do necessário
5. **Segurança técnica**: criptografia em repouso e em trânsito

## Checklist de Revisão
- [ ] Dados de menores criptografados?
- [ ] Consentimento registrado com data/hora?
- [ ] Rotas de exclusão de dados existem?
- [ ] Logs não expõem dados sensíveis?
- [ ] Acesso ao financeiro restrito por perfil?

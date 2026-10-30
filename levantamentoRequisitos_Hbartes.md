# BRIEFING DE ENTREVISTA E LEVANTAMENTO DE REQUISITOS
**Projeto:** Sistema para Escola de Artes  
**Cliente:** Helena Barufaldi  
**Data:** [05/10/26]  
**Responsável pelo levantamento:** Jorge Carneiro  
**Versão:** [1.0]
**Site:** hbartes.netlify.app

## 1. Objetivo do documento
Orientar a entrevista com o cliente, mapear processos, identificar dores, definir escopo inicial e registrar requisitos funcionais e não funcionais.

## 2. Dados gerais do cliente
- Nome da escola: Escola de Artes Helena Barufaldi
- Unidade: R. Duque de Caxias, 660 - Centro, Nova Odessa - SP, 13460-000
- Modalidades oferecidas: Desenho Publicitário, Desenho Artístico, Desenho Moda, Desenho Infantil, Óleo sobre tela, Aquarela, Arteterapia, Fotografia, Mangá
- Público: infantil, juvenil, adulto e terceira idade
- Nº aproximado de alunos: 60
- Nº de professores: 5
- Nº de turmas: 13
divididas por horários
Quinta manhã
terça tarde
terça noite
sábados manhã
sabado tarde 

- Nº de salas/estúdios: 6
Sala 1 - 6
- Sazonalidade: matrículas, férias, espetáculos, recitais.
- Sistemas atuais: planilhas, caderno, sistema antigo, WhatsApp, e-mail?
- Principais dores hoje: Financeiro

## 3. Objetivos do projeto
- O que motivou a buscar um sistema?
Falta de organização, hoje é feito tudo a mão

- Quais problemas precisam ser resolvidos?
Centralizar tudo em um unico sistema, Cadastro de alunos e responsáveis, professores, controle de turmas e salas

- O que precisa melhorar: matrícula, cobrança, frequência, comunicação e relatórios.

- Como medir sucesso? 
reduzir inadimplência, tempo de matrícula, faltas, retrabalho.

- Restrições de prazo, orçamento e equipe.


## 4. Stakeholders e perfis de usuário
| Perfil | Interesse | Permissões esperadas | Dores |
|---|---|---|---|
| Direção | Visão gerencial, relatórios | Acesso total | Falta de indicadores |
| Coordenação pedagógica | Turmas, professores, avaliações | Gestão pedagógica | Processos manuais |
| Secretaria | Matrículas, cadastros, documentos | Cadastros e matrículas | Retrabalho |
| Financeiro | Cobranças, pagamentos, inadimplência | Financeiro | Conciliação e cobrança |
| Professores | Frequência, notas, materiais | Lançamentos | Falta de agilidade |
| Alunos | Aulas, pagamentos, materiais | Consulta | Pouca comunicação |
| Responsáveis | Pagamentos, frequência, comunicados | Consulta e autorizações | Falta de transparência |

## 5. Módulos candidatos
Marque o que faz sentido para o projeto:

- X Cadastro de alunos, responsáveis e professores
- X Matrícula e rematrícula e cadastro dos cursos
- X Turmas, horários, salas e professores
- X Aula experimental e lista de espera
- X Frequência e diário de classe
- x Reposição de aulas
- X Avaliações, boletins, relatórios descritivos e portfólio
- X Financeiro: mensalidades, planos, descontos, bolsas, multas
- X Pagamentos: PIX, boleto, cartão, recorrência
- X Inadimplência e régua de cobrança
- X Comunicação: WhatsApp, e-mail, mural
- x Portal do professor
- X Relatórios e dashboards

## 6. Perguntas por área

### 6.1 Alunos e responsáveis
- Dados obrigatórios:
Nome do Aluno, Data Nascimento.
Caso menor:
Nome responsável, CPF, Endereço, Telefone, E-Mail

- Há alunos menores de idade, O responsável financeiro, será o responsável no cadastro

- Precisa de autorização de imagem, saúde, alergias, medicações.

- Um aluno não pode ter mais de um responsável.

### 6.2 Professores
- Cadastro e contrato:
Nome, Endereço, Telefone, E-mail, Especialidades, Disponibilidade, Substituos
- Professores têm disponibilidade, especialidades, substitutos.
- Professor Quem lança frequência, notas e materiais


### 6.3 Turmas, horários e salas
- Como as turmas são montadas? Por idade, nível, modalidade, dia/hora:
Por idade infantil de 7 - 10, Juvenil 11 - 17, Adulto 18 - 65, terceira idade acima de 65
- Há capacidade máxima, lista de espera, conflitos de sala/professor:
Capacidade máxima 9 por sala

- Aulas são recorrentes Aulas 1x por semana, aulas experimentais/cortesias, reposições, feriados:


### 6.4 Matrícula e rematrícula
- Matrícula depende da duração do curso.

- Renovação não é automática, e feita por contrato assinado.

- Não há pré-requisitos

- Descontos: irmãos, indicação, bolsa.

- Cancelamento e trancamento: multa, aviso prévio regidos em contrato.

### 6.5 Financeiro
- Formas de pagamento aceitas: Pix, Cartão, Boleto, Dinheiro

- Planos, pacotes, aulas avulsas

- Bolsas, descontos, multas, juros, negociação.

- Régua de cobrança e bloqueio de acesso.

- Precisa conciliação, fluxo de caixa, DRE?
Sim

### 6.6 Frequência e pedagógico
- Chamada por aula.

- Reposições feitas dentro do proprio mês ou na primeira semana do mês seguinte.

- Avaliações: notas, conceitos, relatórios descritivos.

- Boletim, certificado, portfólio.

- Diário de classe e plano de aula.

### 6.7 Comunicação
- Canais preferidos: WhatsApp, e-mail.
- Lembretes de pagamento, aula, evento

### 6.8 Eventos
- Exposições, workshops.
- Inscrições, ingressos, pagamentos, lista de presença.
- Autorização de imagem e transporte

### 6.10 Relatórios e dashboards
- Alunos ativos/inativos, inadimplência, ocupação de turmas.
- Frequência, desempenho, professores, financeiro.
- Exportação Excel/PDF.

## 7. Requisitos não funcionais
- Web, Responsivo
- servidor local
- Nº de usuários: 2
- Disponibilidade, backup e recuperação.


## 8. Priorização MoSCoW
- **Must:** essencial para operar.
- **Should:** importante, mas não bloqueante.
- **Could:** desejável.
- **Won’t:** fora do escopo nesta fase.

## 10. Entregáveis do levantamento
- Documento de visão.
- Escopo funcional.
- Backlog de épicos e user stories.
- Protótipos/wireframes.
- Requisitos não funcionais.
- Critérios de aceite.
- Matriz de rastreabilidade.
- Cronograma e orçamento.
- Plano de implantação e treinamento.


## 13. Template de registro de requisito
| ID | Módulo | Requisito | Tipo | Prioridade | Regra de negócio | Critério de aceite | Status |
|---|---|---|---|---|---|---|---|
| RF001 | Matrícula | Permitir matrícula online | Funcional | Must | Aluno deve ter responsável financeiro | Matrícula gera contrato e cobrança | A definir |

---
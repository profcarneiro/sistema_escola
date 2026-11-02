import urllib.parse
from datetime import date
from typing import Optional


def formatar_telefone_whatsapp(telefone: str) -> str:
    """Higieniza telefone brasileiro adicionando DDI 55 se ausente."""
    numeros = "".join(filter(str.isdigit, telefone))
    if len(numeros) == 10 or len(numeros) == 11:
        return f"55{numeros}"
    elif len(numeros) == 12 or len(numeros) == 13:
        return numeros
    return numeros


def gerar_link_whatsapp(telefone: str, mensagem: str) -> str:
    """Gera link direto para abertura no WhatsApp Web ou Mobile."""
    tel_limpo = formatar_telefone_whatsapp(telefone)
    msg_encoded = urllib.parse.quote(mensagem)
    return f"https://wa.me/{tel_limpo}?text={msg_encoded}"


def mensagem_lembrete_cobranca(
    nome_responsavel_ou_aluno: str,
    nome_aluno: str,
    descricao_titulo: str,
    valor: float,
    data_vencimento: date,
    chave_pix: str = "pix@hbartes.com.br"
) -> str:
    """Template de mensagem para régua de cobrança/lembrete de mensalidade."""
    venc_str = data_vencimento.strftime("%d/%m/%Y")
    return (
        f"Olá, {nome_responsavel_ou_aluno}! 👋\n\n"
        f"Lembramos que a {descricao_titulo} referente ao aluno(a) *{nome_aluno}* "
        f"na *Escola de Artes Helena Barufaldi* vence em *{venc_str}* no valor de *R$ {valor:.2f}*.\n\n"
        f"🔑 Chave PIX da escola: {chave_pix}\n\n"
        f"Caso já tenha efetuado o pagamento, por favor desconsidere este aviso. "
        f"Qualquer dúvida, estamos à disposição no atelier! 🎨"
    )


def mensagem_confirmacao_matricula(
    nome_aluno: str,
    modalidade: str,
    dia_semana: str,
    horario: str,
    data_inicio: date
) -> str:
    """Template de boas-vindas e confirmação de matrícula."""
    inicio_str = data_inicio.strftime("%d/%m/%Y")
    return (
        f"Olá! 🎉 Seja muito bem-vindo(a) à *Escola de Artes Helena Barufaldi*!\n\n"
        f"A matrícula de *{nome_aluno}* na modalidade *{modalidade}* foi confirmada com sucesso.\n"
        f"📅 Aulas: toda(o) {dia_semana}, das {horario}.\n"
        f"🗓️ Início: {inicio_str}.\n\n"
        f"Estamos ansiosos para criar muita arte juntos! Nos vemos no atelier! 🎨✨"
    )

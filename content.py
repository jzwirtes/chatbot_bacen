# ALTERAR AS DATAS PARA TESTES
import requests
from bs4 import BeautifulSoup
import re
import unicodedata
from urllib.parse import quote


ALLOWED_TYPES = {
    "resolução cmn": "Resolução CMN",
    "resolução bcb": "Resolução BCB",
    "instrução normativa bcb": "Instrução Normativa BCB",
    "circular": "Circular",
    "carta circular": "Carta Circular",
    "resolução conjunta": "Resolução Conjunta"
}

def fetch_normativo(tipo: str, numero: str, timeout: float = 100000.0) -> dict:
    """
    Busca o normativo no BCB e retorna o JSON decodificado.

    Args:
        tipo: um dos valores em ALLOWED_TYPES (case-insensitive)
        numero: string ou número representando o identificador (p2)
        timeout: tempo máximo de espera em segundos

    Returns:
        dict com o conteúdo JSON do normativo.

    Raises:
        ValueError: se o tipo não for válido.
        requests.HTTPError: em caso de status code != 200.
        requests.RequestException: em erros de conexão/timeouts.
    """
    # normaliza e valida o tipo
    key = tipo.strip().lower()
    if key not in ALLOWED_TYPES:
        raise ValueError(f"tipo inválido: {tipo!r}. Use um de: {list(ALLOWED_TYPES.values())}")
    p1 = ALLOWED_TYPES[key]
    
    url = "https://www.bcb.gov.br/api/conteudo/app/normativos/exibenormativo"
    params = {
        "p1": p1,
        "p2": str(int(float(numero))),
    }

    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def limpar_texto_html(html: str) -> str:
    """
    Remove todas as tags HTML e normaliza espaços em branco,
    além de:
      - normalizar Unicode (NFKC)
      - converter non-breaking spaces (\xa0) em espaço simples
      - remover caracteres de controle Unicode
      - garantir que termine em caractere visível (sem espaços finais)
    """
    # 1) Parse do HTML
    soup = BeautifulSoup(html, 'html.parser')
    # 2) Extrai só o texto, usando espaço como separador
    texto = soup.get_text(separator=' ')
    
    # 3) Normaliza Unicode (combina acentos, etc.)
    texto = unicodedata.normalize('NFKC', texto)
    # 4) Substitui NBSP por espaço normal
    texto = texto.replace('\u00A0', ' ')
    # 5) Remove tabs, quebras de linha e semelhantes
    texto = re.sub(r'[\r\n\t]+', ' ', texto)
    # 6) Remove quaisquer outros caracteres de controle
    texto = ''.join(
        ch for ch in texto
        if unicodedata.category(ch)[0] != 'C'
    )
    # 7) Agrupa múltiplos espaços em um só
    texto = re.sub(r' {2,}', ' ', texto)
    # 8) Remove espaço no início e no fim
    texto = texto.strip()
    
    # 9) Garante que termine em caractere visível (letra, dígito ou pontuação)
    if texto and not re.match(r'.*[\w\.\,\;\:\!\?]$', texto):
        texto += '.'
    
    return texto

def fetch_normativos_por_termos(termos, ini_date, end_date, row_limit=15):
    """
    Busca normativos do Banco Central por palavras-chave e intervalo de datas.

    Args:
        termos (list[str]): Lista de palavras-chave (ex: ['provisão', 'risco de crédito'])
        ini_date (str): Data inicial no formato 'YYYY-MM-DD'
        end_date (str): Data final no formato 'YYYY-MM-DD'
        row_limit (int): Número de registros por página (padrão: 15)

    Returns:
        list[dict]: Lista de normativos encontrados
    """
    base_url = "https://www.bcb.gov.br/api/search/app/normativos/buscanormativos"

    # Junta os termos com " OR " e faz URL encode
    termos_query = quote(" OR ".join(termos))

    querytext = f"ContentType:normativo AND contentSource:normativos AND {termos_query}"
    refinementfilters = f"Data:range(datetime({ini_date}),datetime({end_date}))"

    startrow = 0
    all_results = []

    while True:
        params = {
            "querytext": querytext,
            "rowlimit": row_limit,
            "startrow": startrow,
            "sortlist": "Data1OWSDATE:descending",
            "refinementfilters": refinementfilters
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        rows = data.get("Rows", [])
        if not rows:
            break

        for item in rows:
            # Limpeza opcional de alguns campos HTML
            resumo = item.get("HitHighlightedSummary", "")
            item["HitHighlightedSummary"] = re.sub(r"<[^>]+>", "", resumo)
            assunto = item.get("AssuntoNormativoOWSMTXT", "")
            item["AssuntoNormativoOWSMTXT"] = re.sub(r"<[^>]+>", "", assunto)

        all_results.extend(rows)

        # Condição de parada: menos resultados do que o limite = última página
        if len(rows) < row_limit:
            break

        startrow += row_limit

    all_results = [i for i in all_results if "Comunicado" not in i.get('title')] 
    return all_results

def fetch_normativos_list(ini_date: str, end_date: str, limit: int = 30, start_row: int = 0, timeout: float = 1000.0) -> dict:
    """
    Retorna a lista de normativos publicados entre ini_date e end_date.

    Args:
        ini_date (str): Data inicial no formato 'YYYY-MM-DD'.
        end_date (str): Data final no formato 'YYYY-MM-DD'.
        limit (int): Número máximo de registros a retornar.
        start_row (int): Índice inicial para paginação.
        timeout (float): Tempo máximo de espera para a requisição.

    Returns:
        dict: JSON decodificado da resposta com a lista de normativos.
    """
    
    BASE_SEARCH_URL = "https://www.bcb.gov.br/api/search/app/normativos/buscanormativos"
    params = {
        "querytext": "ContentType:normativo AND contentSource:normativos",
        "rowlimit": limit,
        "startrow": start_row,
        "sortlist": "Data1OWSDATE:descending",
        "refinementfilters": f"Data:range(datetime({ini_date}),datetime({end_date}))"
    }

    response = requests.get(BASE_SEARCH_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()
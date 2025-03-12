import re

try:
    from unidecode import unidecode
    HAS_UNIDECODE = True
except ImportError:
    HAS_UNIDECODE = False

# Dicionário TUSS, com (nome_exame, "imagem"/"nao_imagem")
TUSS_EXAMS = {
    40901114: ("Ultrassonografia", "imagem"),
    40501012: ("Tomografia Computadorizada", "imagem"),
    40601110: ("Ressonância Magnética", "imagem"),
    40901113: ("Mamografia", "imagem"),
    40801013: ("Radiografia", "imagem"),
    40101015: ("Colonoscopia", "nao_imagem"),
    40701121: ("Endoscopia", "nao_imagem"),
}

# Regex para texto não estruturado: (regex, exame_final, ex_type)
EXAM_PATTERNS = [
    (r'(ressonancia|ressonnancia|ressonância|rm|ressonfncia)', "Ressonância Magnética", "imagem"),
    (r'(tomografia|tc)', "Tomografia Computadorizada", "imagem"),
    (r'(ultrassom|ultrassonografia)', "Ultrassonografia", "imagem"),
    (r'(radiografia|raio\-x|raiox)', "Radiografia", "imagem"),
    (r'(mamografia|mamas)', "Mamografia", "imagem"),
    (r'colonoscop', "Colonoscopia", "nao_imagem"),
    (r'endoscop', "Endoscopia", "nao_imagem"),
]

# Termos que indicam "sem exame" ou "checkup"
IGNORE_TERMS = {
    "sem exame", "exame não especificado", "apenas checkup",
    "sem exame adicional", "checkup geral", "apenas checkup geral"
}

def normalize_text(txt):
    """
    Normaliza texto para facilitar o match:
    1) Converte para minúsculas
    2) Remove acentos (unidecode) se tiver.
    3) Substitui 'fncia' por 'nancia' (ex.: 'ressonfncia' para 'ressonancia')
    4) Remove termos irrelevantes
    5) Remove múltiplos espaços
    """
    if not txt:
        return ""
    txt_lower = txt.lower()
    if HAS_UNIDECODE:
        txt_lower = unidecode(txt_lower)
    txt_lower = re.sub(r'fncia', 'nancia', txt_lower)
    txt_lower = re.sub(r'\b(adicional|recomendada|programada|do|da|de)\b', '', txt_lower)
    txt_lower = re.sub(r'\s+', ' ', txt_lower).strip()
    return txt_lower

def classify_exam(cd_tuss, ds_receita):
    """
    1) Se cd_tuss estiver em TUSS_EXAMS (exame, ex_type)
    2) Caso contrário  normaliza ds_receita e casa com EXAM_PATTERNS
    3) Se nada encontrado = "Sem Exame"
    """
    if cd_tuss and cd_tuss in TUSS_EXAMS:
        return TUSS_EXAMS[cd_tuss]
    norm = normalize_text(ds_receita)
    if not norm or norm in IGNORE_TERMS:
        return ("Sem Exame", "nao_imagem")
    for (rgx, exame_final, ex_type) in EXAM_PATTERNS:
        if re.search(rgx, norm, re.IGNORECASE):
            return (exame_final, ex_type)
    return (norm.title(), "nao_imagem")

def build_message_for_exams(client_name, exam_list):
    """
    Recebe exam_list = [(exame, ex_type), ...].
    Deduplica, remove "Sem Exame" e IGNORE_TERMS, e formata a mensagem.
    """
    from config.settings import PLATFORM_LINK, COMPANY_NAME  # Import local para evitar dependência circular
    unique_img = set()
    unique_nonimg = set()

    for (exame, ex_type) in exam_list:
        ex_lower = exame.lower()
        if ex_lower in IGNORE_TERMS or ex_lower.startswith("sem exame"):
            continue
        if ex_type == "imagem":
            unique_img.add(exame)
        else:
            unique_nonimg.add(exame)

    img_list = sorted(unique_img)
    nonimg_list = sorted(unique_nonimg)

    lines = []
    lines.append(f"Olá {client_name},")
    lines.append("")
    lines.append("Identificamos que você tem alguns exames pendentes:")
    lines.append("")

    bullet_lines = []
    for item in img_list:
        bullet_lines.append(f"• {item}")
    for item in nonimg_list:
        bullet_lines.append(f"• {item}")

    if bullet_lines:
        lines.extend(bullet_lines)
    else:
        lines.append("• Nenhum exame específico identificado.")

    lines.append("")
    lines.append("É fundamental agendar o quanto antes para garantir sua saúde em dia.")
    lines.append(f"Agende facilmente pelo link: {PLATFORM_LINK}")
    lines.append("")
    lines.append(f"Caso precise de suporte, a equipe {COMPANY_NAME} está aqui para ajudar.")
    lines.append("")
    lines.append("Um abraço,")
    lines.append(f"Equipe {COMPANY_NAME}")

    return "\n".join(lines)

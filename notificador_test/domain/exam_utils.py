import re

try:
    from unidecode import unidecode
    HAS_UNIDECODE = True
except ImportError:
    HAS_UNIDECODE = False

# Dicionário TUSS com tuplas (exame, pronome, tipo)
TUSS_EXAMS = {
    40901114: ("Ultrassonografia", "sua", "imagem"),
    40501012: ("Tomografia Computadorizada", "sua", "imagem"),
    40601110: ("Ressonância Magnética", "sua", "imagem"),
    40901113: ("Mamografia", "sua", "imagem"),
    40801013: ("Radiografia", "sua", "imagem"),
    40101015: ("Colonoscopia", "sua", "nao_imagem"),
    40701121: ("Endoscopia", "sua", "nao_imagem")
}

# Dicionário de padrões para exames
exam_patterns = {
    "tomografia computadorizada": {
        "pattern": re.compile(r'\b(?:tomografia|tc)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "ressonância magnética": {
        "pattern": re.compile(r'\b(?:ressonancia|rm|ressonância)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "ultrassonografia": {
        "pattern": re.compile(r'\b(?:ultrassom|ultrassonografia)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "radiografia": {
        "pattern": re.compile(r'\b(?:radiografia|raio-x|raiox)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "mamografia": {
        "pattern": re.compile(r'\b(?:mamografia|mamas)\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "imagem"
    },
    "colonoscopia": {
        "pattern": re.compile(r'\bcolonoscopia\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "nao_imagem"
    },
    "endoscopia": {
        "pattern": re.compile(r'\bendoscopia\b', re.IGNORECASE),
        "pronoun": "sua",
        "type": "nao_imagem"
    }
}

# Termos a serem ignorados
ignore_terms = {
    "sem exame", "exame não especificado", "apenas checkup", "sem exame adicional"
}

def normalize_text(txt):
    if not txt:
        return ""
    txt_lower = txt.lower()
    if HAS_UNIDECODE:
        txt_lower = unidecode(txt_lower)
    txt_lower = re.sub(r'\b(adicional|recomendada|programada|do|da|de)\b', '', txt_lower)
    txt_lower = re.sub(r'\s+', ' ', txt_lower).strip()
    return txt_lower

def classify_exam(cd_tuss, ds_receita):
    if cd_tuss and cd_tuss in TUSS_EXAMS:
        return TUSS_EXAMS[cd_tuss]
    norm = normalize_text(ds_receita)
    if not norm or norm in ignore_terms:
        return ("Sem Exame", "seu", "nao_imagem")
    for cat, info in exam_patterns.items():
        if info["pattern"].search(norm):
            return (cat.title(), info["pronoun"], info["type"])
    return (norm.title(), "seu", "nao_imagem")

def build_message_for_exams(client_name, exam_list):
    from config.settings import PLATFORM_LINK, COMPANY_NAME
    unique_image = set()
    unique_non_image = set()

    for (cat, pron, ex_type) in exam_list:
        cat_lower = cat.lower()
        if cat_lower in ignore_terms or cat_lower.startswith("sem exame"):
            continue
        if ex_type == "imagem":
            unique_image.add((cat, pron))
        else:
            unique_non_image.add((cat, pron))

    image_list_str = sorted([f"{pron} {cat}" for (cat, pron) in unique_image])
    non_image_list_str = sorted([f"exame de {cat}" for (cat, pron) in unique_non_image])

    lines = []
    lines.append(f"Olá {client_name},")
    lines.append("")
    lines.append("Identificamos que você tem alguns exames pendentes:")
    lines.append("")

    bullet_lines = []
    for item in image_list_str:
        bullet_lines.append(f"• {item}")
    for item in non_image_list_str:
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

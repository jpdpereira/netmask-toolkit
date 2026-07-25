"""
vendors.py - perfis de padroes de linha (hostname, descricao de porta,
campos LLDP/CDP) por plataforma.

Cada perfil e uma lista de tuplos:
    (categoria, regex_compilado, usa_aspas)

- categoria: nome livre, vira o prefixo do token (ex: "HOSTNAME_001")
- regex_compilado: DEVE ter exatamente 2 grupos de captura:
    grupo 1 -> prefixo da linha (mantido tal e qual)
    grupo 2 -> o valor sensivel, SEM aspas mesmo que a sintaxe as use
- usa_aspas: True se a sintaxe original envolve o valor em aspas duplas
  (o core.py trata de as adicionar de volta no output mascarado)

Isto e conhecimento de dominio (sintaxe real de cada plataforma) e e o
UNICO sitio que precisa de ser tocado para adicionar suporte a um novo
vendor -- nao mexer em core.py.

Nota: os padroes de LLDP/CDP (NEIGHBOR/PORTID) foram escritos a partir do
formato tipico de "show" output de cada plataforma. Se um ficheiro real
tiver um formato ligeiramente diferente do teu equipamento, ajusta aqui
o regex correspondente -- e so isso que precisa de mudar.
"""

import re

_MI = re.MULTILINE | re.IGNORECASE

VENDOR_PROFILES = {
    # Cisco IOS / IOS-XE
    "cisco": [
        ("HOSTNAME", re.compile(r"^(\s*hostname\s+)(\S+)", _MI), False),
        ("DESC", re.compile(r"^(\s*description\s+)(.+)$", _MI), False),
        ("NEIGHBOR", re.compile(r"^(\s*(?:System Name|Device ID)\s*[:\-]\s*)(\S+)", _MI), False),
        ("PORTID", re.compile(r"^(\s*Port ID \(outgoing port\)\s*[:\-]\s*)(.+)$", _MI), False),
        ("SNMP_COMMUNITY", re.compile(r"^(\s*snmp-server community\s+)(\S+)", _MI), False),
        ("SNMP_CONTACT", re.compile(r"^(\s*snmp-server contact\s+)(.+)$", _MI), False),
        ("SNMP_LOCATION", re.compile(r"^(\s*snmp-server location\s+)(.+)$", _MI), False),
    ],

    # HPE Aruba AOS-Switch (ex-ProVision/ProCurve: 2530, 2920, 2930...)
    "aruba-switch": [
        ("HOSTNAME", re.compile(r'^(\s*hostname\s+)"([^"]*)"', _MI), True),
        ("DESC", re.compile(r'^(\s*name\s+)"([^"]*)"', _MI), True),          # "description" chama-se "name" nesta plataforma
        ("NEIGHBOR", re.compile(r"^(\s*SysName\s*:\s*)(\S+)", _MI), False),  # show lldp info remote-device
        ("PORTID", re.compile(r"^(\s*PortDescr\s*:\s*)(.+)$", _MI), False),
        # credencial SNMP (equivalente a uma password) -- gap real encontrado ao testar com dados reais
        ("SNMP_COMMUNITY", re.compile(r'^(\s*snmp-server community\s+)"([^"]*)"', _MI), True),
        ("SNMP_CONTACT", re.compile(r'(snmp-server contact\s+)"([^"]*)"', _MI), True),
        ("SNMP_LOCATION", re.compile(r'(location\s+)"([^"]*)"', _MI), True),
    ],

    # HPE Aruba AOS-CX
    "aruba-cx": [
        ("HOSTNAME", re.compile(r"^(\s*hostname\s+)(\S+)", _MI), False),
        ("DESC", re.compile(r'^(\s*description\s+)"([^"]*)"', _MI), True),
        ("NEIGHBOR", re.compile(r"^(\s*Neighbor Name\s*:\s*)(\S+)", _MI), False),
        ("PORTID", re.compile(r"^(\s*Neighbor Port-Description\s*:\s*)(.+)$", _MI), False),
    ],

    # HPE Comware (v5/v7)
    "comware": [
        ("HOSTNAME", re.compile(r"^(\s*sysname\s+)(\S+)", _MI), False),
        ("DESC", re.compile(r"^(\s*description\s+)(.+)$", _MI), False),
        ("NEIGHBOR", re.compile(r"^(\s*System name\s*:\s*)(\S+)", _MI), False),
        ("PORTID", re.compile(r"^(\s*Port description\s*:\s*)(.+)$", _MI), False),
    ],

    # Juniper JunOS (estilo "set")
    "juniper": [
        ("HOSTNAME", re.compile(r"^(\s*set system host-name\s+)([^;\s]+)", _MI), False),
        ("DESC", re.compile(r'^(\s*set interfaces \S+ description\s+)"([^"]*)"', _MI), True),
        ("NEIGHBOR", re.compile(r"^(\s*System Name\s*:\s*)(\S+)", _MI), False),
        ("PORTID", re.compile(r"^(\s*Port Description\s*:\s*)(.+)$", _MI), False),
    ],

    # FortiOS (FortiGate)
    "fortios": [
        ("HOSTNAME", re.compile(r'^(\s*set hostname\s+)"([^"]*)"', _MI), True),
        ("DESC", re.compile(r'^(\s*set alias\s+)"([^"]*)"', _MI), True),        # descricao de interface = "alias"
        ("DESC", re.compile(r'^(\s*set description\s+)"([^"]*)"', _MI), True), # description generico noutros objetos
    ],

    # Check Point Gaia (clish)
    "checkpoint": [
        ("HOSTNAME", re.compile(r"^(\s*set hostname\s+)(\S+)", _MI), False),
        ("DESC", re.compile(r'^(\s*set interface \S+ description\s+)"([^"]*)"', _MI), True),
    ],

    # UniFi / Ubiquiti (EdgeOS/vyatta-style, ex: EdgeRouter)
    "unifi": [
        ("HOSTNAME", re.compile(r"^(\s*set system host-name\s+)([^;\s]+)", _MI), False),
        ("DESC", re.compile(r'^(\s*set interfaces \S+ \S+ description\s+)"([^"]*)"', _MI), True),
    ],

    # Fallback: so os padroes mais universais (estilo Cisco), para quando
    # nao se sabe o vendor ou se quer uma primeira passagem rapida
    "generic": [
        ("HOSTNAME", re.compile(r"^(\s*(?:hostname|sysname)\s+)(\S+)", _MI), False),
        ("DESC", re.compile(r"^(\s*description\s+)(.+)$", _MI), False),
        ("NEIGHBOR", re.compile(r"^(\s*(?:System Name|Device ID|SysName)\s*[:\-]\s*)(\S+)", _MI), False),
        ("PORTID", re.compile(r"^(\s*(?:Port ID \(outgoing port\)|PortDescr|Port [Dd]escription)\s*[:\-]\s*)(.+)$", _MI), False),
        ("SNMP_COMMUNITY", re.compile(r"^(\s*snmp-server community\s+)(\S+)", _MI), False),
        ("SNMP_CONTACT", re.compile(r"^(\s*snmp-server contact\s+)(.+)$", _MI), False),
        ("SNMP_LOCATION", re.compile(r"^(\s*snmp-server location\s+)(.+)$", _MI), False),
    ],
}


def get_profile(vendor):
    try:
        return VENDOR_PROFILES[vendor]
    except KeyError:
        raise ValueError(
            f"Vendor '{vendor}' desconhecido. Opcoes: {', '.join(sorted(VENDOR_PROFILES))}"
        )


# ---------- deteccao automatica de vendor ----------
# Cada vendor tem uma lista de "assinaturas" (regex) tipicas da sua sintaxe.
# O vendor com mais assinaturas encontradas no ficheiro ganha. Isto e uma
# heuristica, nao uma deteccao garantida -- em caso de duvida ou empate,
# usa sempre "generic" ou pede ao utilizador para especificar --vendor.
VENDOR_SIGNATURES = {
    "cisco": [
        re.compile(r"^\s*ip address\s+\S+\s+\S+\s*$", _MI),
        re.compile(r"^!\s*$", re.MULTILINE),
        re.compile(r"Device ID\s*:", _MI),
        re.compile(r"^\s*mac-address\s+", _MI),
    ],
    "aruba-switch": [
        re.compile(r'^\s*hostname\s+"', _MI),
        re.compile(r'^\s*name\s+"', _MI),
        re.compile(r"^\s*no lacp\s*$", _MI),
        re.compile(r"^\s*PortDescr\s*:", _MI),
    ],
    "aruba-cx": [
        re.compile(r'^\s*description\s+"', _MI),
        re.compile(r"Neighbor Port-Description\s*:", _MI),
        re.compile(r"Neighbor Chassis-ID\s*:", _MI),
    ],
    "comware": [
        re.compile(r"^\s*sysname\s+\S+", _MI),
        re.compile(r"System name\s*:", _MI),
        re.compile(r"Chassis ID\s*:", _MI),
    ],
    "juniper": [
        re.compile(r"^\s*set system host-name\s+", _MI),
        re.compile(r"^\s*set interfaces \S+ unit \d+", _MI),
        re.compile(r"family inet", _MI),
    ],
    "fortios": [
        re.compile(r"^\s*config system global\s*$", _MI),
        re.compile(r'^\s*set hostname\s+"', _MI),
        re.compile(r'^\s*set alias\s+"', _MI),
    ],
    "checkpoint": [
        re.compile(r"^\s*set interface \S+ description\s+", _MI),
        re.compile(r"^\s*set static-route\s+", _MI),
    ],
    "unifi": [
        re.compile(r"^\s*set system host-name\s+", _MI),
        re.compile(r"^\s*set interfaces ethernet\s+", _MI),
    ],
}


def detect_vendor(text):
    """Devolve (vendor, score) com base em quantas assinaturas batem.
    Se nenhum vendor tiver pelo menos 1 assinatura, devolve (None, 0)."""
    scores = {}
    for vendor, signatures in VENDOR_SIGNATURES.items():
        scores[vendor] = sum(1 for pattern in signatures if pattern.search(text))

    best_vendor = max(scores, key=scores.get)
    best_score = scores[best_vendor]
    if best_score == 0:
        return None, 0
    return best_vendor, best_score

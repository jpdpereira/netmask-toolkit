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
    ],

    # HPE Aruba AOS-Switch (ex-ProVision/ProCurve: 2530, 2920, 2930...)
    "aruba-switch": [
        ("HOSTNAME", re.compile(r'^(\s*hostname\s+)"([^"]*)"', _MI), True),
        ("DESC", re.compile(r'^(\s*name\s+)"([^"]*)"', _MI), True),          # "description" chama-se "name" nesta plataforma
        ("NEIGHBOR", re.compile(r"^(\s*SysName\s*:\s*)(\S+)", _MI), False),  # show lldp info remote-device
        ("PORTID", re.compile(r"^(\s*PortDescr\s*:\s*)(.+)$", _MI), False),
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
    ],
}


def get_profile(vendor):
    try:
        return VENDOR_PROFILES[vendor]
    except KeyError:
        raise ValueError(
            f"Vendor '{vendor}' desconhecido. Opcoes: {', '.join(sorted(VENDOR_PROFILES))}"
        )

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from imc_mask import IMCMapper, _site_code, mask_devices_csv

HEADER = (
    "Status,Device Label,Model,IP Address,Vendor,Device Category,Location,"
    "Contact,CPU Usage (%),Memory Usage (%),Response Time of Device (ms),"
    "Device Unreachability Proportion (%),"
    "IP Datagram Receiving Rate (datagrams/s),"
    "IP Datagram Forwarding Rate (datagrams/s),"
    "Discarded Proportion of Input IP Datagrams (%),"
    "Discarded Proportion of Output IP Datagrams (%),"
    "Serial Number,Software Version,Rack"
)

ROW1 = 'Normal,SW-CORE-01,5710,10.45.12.7,HPE,Switch,"Edificio Norte",Joao Silva,12,34,5,0,120,110,0,0,CN12345ABC,7.1.070,RACK-PHYS-1'
ROW2 = 'Critical,SW-ACC-02,2930,10.45.200.13,Aruba,Switch,"Edificio Norte",Joao Silva,,,,100,,,,,CN12345ABC,16.11.0020,RACK-PHYS-1'
ROW3 = 'Normal,FW-EDGE-01,ASA5525,192.168.10.5,Cisco,Firewall,Armazem Sul,Maria Costa,45,60,2,0,500,480,1,0,CN99999999,9.16,'

SAMPLE_CSV = f"{HEADER}\n{ROW1}\n{ROW2}\n{ROW3}\n"


def _write_csv(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_site_code_generation_beyond_26():
    assert _site_code(1) == "SITE-A"
    assert _site_code(26) == "SITE-Z"
    assert _site_code(27) == "SITE-AA"
    assert _site_code(52) == "SITE-AZ"
    assert _site_code(53) == "SITE-BA"


def test_ip_masking_keeps_last_two_octets_and_is_consistent(tmp_path):
    input_csv = _write_csv(tmp_path, "in.csv", SAMPLE_CSV)
    output_csv = tmp_path / "out.csv"
    mapping_path = tmp_path / "mapping.json"

    mapper = IMCMapper()
    mapper.load(mapping_path)
    mask_devices_csv(input_csv, output_csv, mapper)
    mapper.save(mapping_path)

    rows = _read_rows(output_csv)
    assert rows[0]["IP Address"] == "10.1.12.7"
    assert rows[1]["IP Address"] == "10.1.200.13"  # mesmo prefixo 10.45 -> mesmo 10.1
    assert rows[2]["IP Address"] == "10.2.10.5"     # prefixo diferente (192.168) -> outro token


def test_contact_column_is_dropped(tmp_path):
    input_csv = _write_csv(tmp_path, "in.csv", SAMPLE_CSV)
    output_csv = tmp_path / "out.csv"
    mapper = IMCMapper()
    mask_devices_csv(input_csv, output_csv, mapper)

    rows = _read_rows(output_csv)
    assert "Contact" not in rows[0]
    assert "Joao Silva" not in output_csv.read_text()
    assert "Maria Costa" not in output_csv.read_text()


def test_duplicate_serial_gets_same_token(tmp_path):
    input_csv = _write_csv(tmp_path, "in.csv", SAMPLE_CSV)
    output_csv = tmp_path / "out.csv"
    mapper = IMCMapper()
    mask_devices_csv(input_csv, output_csv, mapper)

    rows = _read_rows(output_csv)
    # ROW1 e ROW2 partilham o mesmo Serial Number real (CN12345ABC)
    assert rows[0]["Serial Number"] == rows[1]["Serial Number"] == "SN-0001"
    assert rows[2]["Serial Number"] == "SN-0002"


def test_duplicate_location_and_rack_get_same_token(tmp_path):
    input_csv = _write_csv(tmp_path, "in.csv", SAMPLE_CSV)
    output_csv = tmp_path / "out.csv"
    mapper = IMCMapper()
    mask_devices_csv(input_csv, output_csv, mapper)

    rows = _read_rows(output_csv)
    assert rows[0]["Location"] == rows[1]["Location"] == "SITE-A"
    assert rows[2]["Location"] == "SITE-B"
    assert rows[0]["Rack"] == rows[1]["Rack"] == "RACK-01"


def test_untouched_columns_are_preserved_exactly(tmp_path):
    input_csv = _write_csv(tmp_path, "in.csv", SAMPLE_CSV)
    output_csv = tmp_path / "out.csv"
    mapper = IMCMapper()
    mask_devices_csv(input_csv, output_csv, mapper)

    rows = _read_rows(output_csv)
    assert rows[0]["Status"] == "Normal"
    assert rows[0]["Model"] == "5710"
    assert rows[0]["CPU Usage (%)"] == "12"
    assert rows[1]["Device Unreachability Proportion (%)"] == "100"
    assert rows[0]["Software Version"] == "7.1.070"


def test_mapping_persists_across_two_runs(tmp_path):
    mapping_path = tmp_path / "mapping.json"

    # execucao 1
    input1 = _write_csv(tmp_path, "in1.csv", SAMPLE_CSV)
    output1 = tmp_path / "out1.csv"
    mapper1 = IMCMapper()
    mapper1.load(mapping_path)
    mask_devices_csv(input1, output1, mapper1)
    mapper1.save(mapping_path)

    # execucao 2 (novo export): 1 dispositivo repetido + 1 novo
    row_repeat = ROW1  # mesmo IP, serial e rack do primeiro export
    row_new = 'Normal,SW-NEW,3810,10.99.1.1,Aruba,Switch,Site Novo,Ana,1,1,1,0,1,1,0,0,CN00000099,16.10,RACK-PHYS-9'
    csv2 = f"{HEADER}\n{row_repeat}\n{row_new}\n"
    input2 = _write_csv(tmp_path, "in2.csv", csv2)
    output2 = tmp_path / "out2.csv"

    mapper2 = IMCMapper()
    mapper2.load(mapping_path)  # carrega o que a execucao 1 gravou
    mask_devices_csv(input2, output2, mapper2)
    mapper2.save(mapping_path)

    rows = _read_rows(output2)
    # o dispositivo repetido tem de manter EXATAMENTE os mesmos tokens da execucao 1
    assert rows[0]["IP Address"] == "10.1.12.7"
    assert rows[0]["Serial Number"] == "SN-0001"
    assert rows[0]["Rack"] == "RACK-01"
    # o novo dispositivo continua a numeracao, nao reinicia
    # (execucao 1 so tinha 2 series distintas: CN12345ABC e CN99999999 -> SN-0001/SN-0002)
    assert rows[1]["Serial Number"] == "SN-0003"
    assert rows[1]["IP Address"].startswith("10.")
    assert rows[1]["IP Address"] != "10.1.12.7"


def test_blank_optional_fields_stay_blank(tmp_path):
    header = HEADER
    row = "Normal,SW-X,Model,,HPE,Switch,,Contact,,,,,,,,,,,"
    csv_content = header + "\n" + row + "\n"
    input_csv = _write_csv(tmp_path, "in.csv", csv_content)
    output_csv = tmp_path / "out.csv"
    mapper = IMCMapper()
    mask_devices_csv(input_csv, output_csv, mapper)

    rows = _read_rows(output_csv)
    assert rows[0]["IP Address"] == ""
    assert rows[0]["Location"] == ""
    assert rows[0]["Serial Number"] == ""
    assert rows[0]["Rack"] == ""


def test_export_summary_preamble_line_is_skipped(tmp_path):
    """Gap real: exports do IMC podem colar uma linha tipo 'Exported 402
    records.' ANTES do cabecalho real. Sem tratamento, o DictReader le essa
    linha como cabecalho e todo o resto (cabecalho real incluido) vira
    'dados' de uma coluna inexistente -- nada e mascarado."""
    csv_with_preamble = f"Exported 3 records.\n{SAMPLE_CSV}"
    input_csv = _write_csv(tmp_path, "in.csv", csv_with_preamble)
    output_csv = tmp_path / "out.csv"
    mapper = IMCMapper()
    mask_devices_csv(input_csv, output_csv, mapper)

    rows = _read_rows(output_csv)
    assert len(rows) == 3
    assert rows[0]["IP Address"] == "10.1.12.7"
    assert rows[0]["Serial Number"] == "SN-0001"
    assert "Contact" not in rows[0]


def test_device_label_embedded_ips_are_masked_hostname_kept(tmp_path):
    """Gap real: 'Device Label' pode trazer IPs colados ao hostname, ex:
    '10.77.1.6( SW-LAB-CORE-01)(10.77.1.8)'. So os IPs devem ser mascarados
    (com o mesmo mapeamento de prefixo da coluna IP Address); o hostname
    fica intacto -- pedido explicito do utilizador."""
    row = (
        'Critical,10.77.1.6( SW-LAB-CORE-01)(10.77.1.8),'
        "HPE FlexFabric-5945-4-slot,10.77.1.6,HPE,Switch,"
        '"Edificio Norte",Joao Silva,1,1,1,0,1,1,0,0,CNXXXX,7.1,RACK-1'
    )
    csv_content = f"{HEADER}\n{row}\n"
    input_csv = _write_csv(tmp_path, "in.csv", csv_content)
    output_csv = tmp_path / "out.csv"
    mapper = IMCMapper()
    mask_devices_csv(input_csv, output_csv, mapper)

    rows = _read_rows(output_csv)
    label = rows[0]["Device Label"]
    assert "SW-LAB-CORE-01" in label  # hostname mantido
    assert "10.77.1.6" not in label
    assert "10.77.1.8" not in label
    # os dois IPs embutidos (mesmo prefixo 10.25) usam o mesmo mapeamento
    # consistente da coluna IP Address (tambem 10.77.1.6 -> mesmo prefixo)
    assert rows[0]["IP Address"].startswith(label.split("(")[0])


def test_malformed_ip_is_left_unchanged_not_crashed(tmp_path):
    header = HEADER
    row = "Normal,SW-X,Model,not-an-ip,HPE,Switch,SiteX,Contact,,,,,,,,,SNX,,"
    csv_content = header + "\n" + row + "\n"
    input_csv = _write_csv(tmp_path, "in.csv", csv_content)
    output_csv = tmp_path / "out.csv"
    mapper = IMCMapper()
    mask_devices_csv(input_csv, output_csv, mapper)

    rows = _read_rows(output_csv)
    assert rows[0]["IP Address"] == "not-an-ip"  # nao mascarado, mas tambem nao rebentou

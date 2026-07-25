import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import Masker
from vendors import VENDOR_PROFILES, detect_vendor, get_profile

CISCO_SAMPLE = """version 15.2
!
hostname SW-CORE01
!
interface GigabitEthernet1/0/1
 description Uplink to SW-CORE01
 ip address 10.20.30.1 255.255.255.0
!
interface GigabitEthernet1/0/2
 description Link to Firewall-EDGE
 mac-address 00:1a:2b:3c:4d:5e
!
ipv6 address 2001:db8:abcd:12::1/64
!
show cdp neighbors detail
Device ID: SW-ACCESS02
  IP address: 10.20.30.5
  Platform: cisco WS-C2960X
Port ID (outgoing port): GigabitEthernet0/24
System Name: SW-ACCESS02.corp.local
!
show mac address-table
  1    aabb.ccdd.eeff    DYNAMIC     Gi1/0/3
!
snmp-server community public-fake RO
snmp-server contact Network Team
snmp-server location Datacenter Floor 2
!
line vty 0 4
 transport input ssh
!
SW-CORE01# show run
SW-CORE01(config)# interface vlan 10
"""

ARUBA_SWITCH_SAMPLE = """hostname "SW-ACCESS-A1"
interface 1
   name "Uplink to Core"
   no lacp
exit
vlan 10
   ip address 192.168.10.1 255.255.255.0
exit
snmp-server community "fake-community-string"
snmp-server contact "Network Team" location "Datacenter Floor 2"
show lldp info remote-device 1

  Port : 1
  ChassisId  : 30 e1 71 aa bb cc
  PortId     : GigabitEthernet0/1
  SysName    : SW-CORE01
  PortDescr  : Uplink to SW-ACCESS-A1
"""

FORTIOS_SAMPLE = """config system global
    set hostname "FW-EDGE01"
end
config system interface
    edit "port1"
        set alias "WAN-ISP1"
        set ip 203.0.113.5 255.255.255.0
    next
end
"""

JUNIPER_SAMPLE = """set system host-name MX-EDGE01
set interfaces ge-0/0/0 description "Uplink to ISP"
set interfaces ge-0/0/0 unit 0 family inet address 198.51.100.1/30
"""

ARUBA_CX_SAMPLE = """hostname SW-CX-CORE01
interface 1/1/1
    description "Uplink to Distribution"
    no shutdown
interface vlan10
    ip address 10.0.10.1/24
!
show lldp neighbor-info
  Port                : 1/1/1
  Neighbor Name       : SW-CX-DIST01
  Neighbor Port-Description : Downlink to Access
  Neighbor Chassis-ID : 00:11:22:33:44:55
"""

COMWARE_SAMPLE = """sysname CORE-SW01
interface GigabitEthernet1/0/1
 description Trunk-to-Distribution
 ip address 172.16.5.1 255.255.255.0
 quit
vlan 10
 name Servers-VLAN
 description Critical-Server-Segment
 quit
#
snmp-agent community read fake-ro-string
snmp-agent sys-info contact Network Team
snmp-agent sys-info location Datacenter Floor 2
#
display lldp neighbor-information
  System name       : ACCESS-SW02
  Port description  : Uplink to Core
  Chassis ID        : 001a-2b3c-4d5e
"""

CHECKPOINT_SAMPLE = """set hostname FW-GATEWAY01
set interface eth0 description "External WAN"
set interface eth1 description "Internal LAN"
set static-route 0.0.0.0/0 nexthop gateway address 203.0.113.1 priority 1
"""

UNIFI_SAMPLE = """set system host-name EDGE-ROUTER01
set interfaces ethernet eth0 description "WAN"
set interfaces ethernet eth1 description "LAN-Trunk"
set interfaces ethernet eth1 address 192.168.1.1/24
"""


def _roundtrip(sample, vendor):
    profile = get_profile(vendor)
    masker = Masker()
    masked = masker.mask(sample, profile)
    restored = masker.unmask(masked)
    return masked, restored


def test_cisco_roundtrip_is_lossless():
    masked, restored = _roundtrip(CISCO_SAMPLE, "cisco")
    assert restored == CISCO_SAMPLE
    assert "10.20.30.1" not in masked
    assert "SW-CORE01" not in masked
    assert "00:1a:2b:3c:4d:5e" not in masked
    assert "2001:db8:abcd:12::1" not in masked
    assert "public-fake" not in masked  # snmp-server community -- e uma credencial
    assert "Network Team" not in masked
    assert "Datacenter Floor 2" not in masked


def test_aruba_switch_roundtrip_is_lossless():
    masked, restored = _roundtrip(ARUBA_SWITCH_SAMPLE, "aruba-switch")
    assert restored == ARUBA_SWITCH_SAMPLE
    assert "SW-ACCESS-A1" not in masked
    assert "Uplink to Core" not in masked
    assert "SW-CORE01" not in masked  # vem do SysName do vizinho
    assert "30 e1 71 aa bb cc" not in masked  # ChassisId, MAC separado por espacos
    assert "fake-community-string" not in masked  # gap real: SNMP community nao mascarada
    assert "Network Team" not in masked
    assert "Datacenter Floor 2" not in masked


def test_mac_address_space_separated_is_masked():
    """ChassisId de HP/Aruba usa MAC separado por espacos (ex: 'ec eb b8 a8 99 00'),
    formato diferente de ':'/'-'/'.' -- gap real encontrado ao testar com dados reais."""
    masker = Masker()
    text = "ChassisId    : ec eb b8 a8 99 00\n"
    masked = masker.mask(text, get_profile("generic"))
    assert "ec eb b8 a8 99 00" not in masked
    assert masker.unmask(masked) == text


def test_fortios_roundtrip_is_lossless():
    masked, restored = _roundtrip(FORTIOS_SAMPLE, "fortios")
    assert restored == FORTIOS_SAMPLE
    assert "FW-EDGE01" not in masked
    assert "WAN-ISP1" not in masked
    assert "203.0.113.5" not in masked


def test_juniper_roundtrip_is_lossless():
    masked, restored = _roundtrip(JUNIPER_SAMPLE, "juniper")
    assert restored == JUNIPER_SAMPLE
    assert "MX-EDGE01" not in masked
    assert "Uplink to ISP" not in masked
    assert "198.51.100.1" not in masked


def test_aruba_cx_roundtrip_is_lossless():
    masked, restored = _roundtrip(ARUBA_CX_SAMPLE, "aruba-cx")
    assert restored == ARUBA_CX_SAMPLE
    assert "SW-CX-CORE01" not in masked
    assert "Uplink to Distribution" not in masked
    assert "SW-CX-DIST01" not in masked
    assert "10.0.10.1" not in masked


def test_comware_roundtrip_is_lossless():
    masked, restored = _roundtrip(COMWARE_SAMPLE, "comware")
    assert restored == COMWARE_SAMPLE
    assert "CORE-SW01" not in masked
    assert "Trunk-to-Distribution" not in masked
    assert "ACCESS-SW02" not in masked
    assert "172.16.5.1" not in masked
    assert "fake-ro-string" not in masked  # snmp-agent community -- credencial
    assert "Network Team" not in masked
    assert "Datacenter Floor 2" not in masked
    assert "Servers-VLAN" not in masked  # vlan "name" -- gap real encontrado em teste real
    assert "Critical-Server-Segment" not in masked


def test_checkpoint_roundtrip_is_lossless():
    masked, restored = _roundtrip(CHECKPOINT_SAMPLE, "checkpoint")
    assert restored == CHECKPOINT_SAMPLE
    assert "FW-GATEWAY01" not in masked
    assert "External WAN" not in masked
    assert "203.0.113.1" not in masked


def test_unifi_roundtrip_is_lossless():
    masked, restored = _roundtrip(UNIFI_SAMPLE, "unifi")
    assert restored == UNIFI_SAMPLE
    assert "EDGE-ROUTER01" not in masked
    assert "LAN-Trunk" not in masked
    assert "192.168.1.1" not in masked


def test_no_false_positive_on_timestamp():
    log_line = "Jul 25 09:12:34: %LINK-3-UPDOWN: Interface changed state\n"
    masker = Masker()
    masked = masker.mask(log_line, get_profile("generic"))
    assert masked == log_line


def test_unmask_uses_own_mapping_only():
    profile = get_profile("cisco")
    masker1 = Masker()
    masked1 = masker1.mask(CISCO_SAMPLE, profile)
    masker2 = Masker()
    assert masker2.unmask(masked1) == masked1


def test_unknown_vendor_raises():
    with pytest.raises(ValueError):
        get_profile("nokia-srsomethingfake")


def test_all_vendor_profiles_are_well_formed():
    """Cada padrao de cada vendor tem de ter exatamente 2 grupos de captura."""
    for vendor, patterns in VENDOR_PROFILES.items():
        for category, regex, wrap_quotes in patterns:
            assert regex.groups == 2, f"{vendor}/{category} deveria ter 2 grupos, tem {regex.groups}"


@pytest.mark.parametrize(
    ("sample", "expected_vendor"),
    [
        (CISCO_SAMPLE, "cisco"),
        (ARUBA_SWITCH_SAMPLE, "aruba-switch"),
        (ARUBA_CX_SAMPLE, "aruba-cx"),
        (COMWARE_SAMPLE, "comware"),
        (JUNIPER_SAMPLE, "juniper"),
        (FORTIOS_SAMPLE, "fortios"),
        (CHECKPOINT_SAMPLE, "checkpoint"),
        (UNIFI_SAMPLE, "unifi"),
    ],
)
def test_detect_vendor_identifies_each_sample_correctly(sample, expected_vendor):
    detected, score = detect_vendor(sample)
    assert detected == expected_vendor
    assert score > 0


def test_detect_vendor_returns_none_for_unrecognizable_text():
    detected, score = detect_vendor("isto nao e uma config de rede de todo.\nsó texto normal.\n")
    assert detected is None
    assert score == 0

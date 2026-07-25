import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import Masker  # noqa: E402
from vendors import get_profile, VENDOR_PROFILES  # noqa: E402


CISCO_SAMPLE = """hostname SW-CORE01
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


def test_aruba_switch_roundtrip_is_lossless():
    masked, restored = _roundtrip(ARUBA_SWITCH_SAMPLE, "aruba-switch")
    assert restored == ARUBA_SWITCH_SAMPLE
    assert "SW-ACCESS-A1" not in masked
    assert "Uplink to Core" not in masked
    assert "SW-CORE01" not in masked  # vem do SysName do vizinho


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

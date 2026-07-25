import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from netmask import Masker  # noqa: E402

SAMPLE = """hostname SW-CORE01
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


def test_roundtrip_is_lossless():
    masker = Masker()
    masked = masker.mask(SAMPLE)
    restored = masker.unmask(masked)
    assert restored == SAMPLE


def test_masking_actually_hides_sensitive_values():
    masker = Masker()
    masked = masker.mask(SAMPLE)
    assert "10.20.30.1" not in masked
    assert "00:1a:2b:3c:4d:5e" not in masked
    assert "SW-CORE01" not in masked
    assert "2001:db8:abcd:12::1" not in masked


def test_no_false_positive_on_timestamp():
    log = "Jul 25 09:12:34: %LINK-3-UPDOWN: Interface changed state\n"
    masker = Masker()
    masked = masker.mask(log)
    assert masked == log


def test_unmask_uses_own_mapping_only():
    masker1 = Masker()
    masked1 = masker1.mask(SAMPLE)
    masker2 = Masker()
    # sem mapping carregado, unmask nao deve alterar nada
    assert masker2.unmask(masked1) == masked1

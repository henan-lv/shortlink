"""services.ip_whitelist 单测。"""

from app.services.ip_whitelist import IpWhitelist, build_whitelist


class TestDisabled:
    def test_disabled_always_allowed(self):
        wl = IpWhitelist(cidrs=["10.0.0.0/8"], enabled=False)
        assert wl.is_allowed("8.8.8.8") is True
        assert wl.is_allowed("1.1.1.1") is True


class TestEnabled:
    def test_within_cidr_allowed(self):
        wl = IpWhitelist(cidrs=["10.0.0.0/8"], enabled=True)
        assert wl.is_allowed("10.1.2.3") is True

    def test_outside_cidr_denied(self):
        wl = IpWhitelist(cidrs=["10.0.0.0/8"], enabled=True)
        assert wl.is_allowed("8.8.8.8") is False

    def test_multiple_cidrs(self):
        wl = IpWhitelist(cidrs=["10.0.0.0/8", "192.168.0.0/16"], enabled=True)
        assert wl.is_allowed("10.0.0.1") is True
        assert wl.is_allowed("192.168.1.1") is True
        assert wl.is_allowed("172.16.0.1") is False

    def test_invalid_cidr_skipped(self):
        wl = IpWhitelist(cidrs=["not-an-ip", "10.0.0.0/8"], enabled=True)
        assert wl.is_allowed("10.0.0.1") is True
        assert wl.is_allowed("8.8.8.8") is False

    def test_enabled_but_no_cidrs_denies_all(self):
        wl = IpWhitelist(cidrs=[], enabled=True)
        assert wl.is_allowed("127.0.0.1") is False

    def test_invalid_ip_denied(self):
        wl = IpWhitelist(cidrs=["0.0.0.0/0"], enabled=True)
        assert wl.is_allowed("not-an-ip") is False


class TestBuild:
    def test_from_csv(self):
        wl = build_whitelist("10.0.0.0/8, 192.168.0.0/16 ,", True)
        assert wl.is_allowed("10.5.5.5") is True
        assert wl.is_allowed("192.168.99.99") is True
        assert wl.is_allowed("8.8.8.8") is False

    def test_from_none(self):
        wl = build_whitelist(None, False)
        assert wl.is_allowed("8.8.8.8") is True

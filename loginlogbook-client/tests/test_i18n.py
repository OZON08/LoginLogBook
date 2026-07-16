from app import i18n


def test_default_is_german():
    i18n.set_language("de")
    assert i18n.t("client.button.login") == "Anmelden"


def test_switch_to_english():
    i18n.set_language("en")
    assert i18n.t("client.button.login") == "Sign in"
    i18n.set_language("de")  # reset for other tests


def test_fallback_to_default_then_key():
    i18n.set_language("en")
    assert i18n.t("does.not.exist") == "does.not.exist"
    i18n.set_language("de")


def test_interpolation():
    i18n.set_language("de")
    assert i18n.t("client.recent.days", days=7) == "Letzte 7 Tage"

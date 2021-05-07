from pycroft.helpers.i18n import deferred_ngettext, deferred_dngettext

from .assertions import assertNumericMessageCorrect


def test_singular():
    singular = "singular"
    plural = "plural"
    n = 1
    m = deferred_ngettext(singular, plural, n)
    assertNumericMessageCorrect(m, singular, plural, n, None, (), {}, singular)


def test_singular_domain():
    singular = "singular"
    plural = "plural"
    n = 1
    domain = "domain"
    m = deferred_dngettext(domain, singular, plural, n)
    assertNumericMessageCorrect(m, singular, plural, n, domain, (), {}, singular)


def test_plural():
    singular = "singular"
    plural = "plural"
    n = 1000
    domain = "domain"
    m = deferred_dngettext(domain, singular, plural, n)
    assertNumericMessageCorrect(m, singular, plural, n, domain, (), {}, plural)

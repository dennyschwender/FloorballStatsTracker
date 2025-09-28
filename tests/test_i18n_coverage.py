import pytest
from app import TRANSLATIONS


@pytest.mark.parametrize('lang', list(TRANSLATIONS.keys()))
def test_index_and_stats_have_translations(client, lang):
    # Set language via POST
    rv = client.post('/set_language', data={'lang': lang}, follow_redirects=True)
    assert rv.status_code in (200, 302)

    # Index page should include the site title in selected language
    rv2 = client.get('/')
    assert rv2.status_code == 200
    title = TRANSLATIONS[lang].get('title')
    assert title.encode('utf-8') in rv2.data

    # Stats page should include 'Stats' translation
    rv3 = client.get('/stats')
    assert rv3.status_code == 200
    stats_label = TRANSLATIONS[lang].get('stats')
    assert stats_label.encode('utf-8') in rv3.data

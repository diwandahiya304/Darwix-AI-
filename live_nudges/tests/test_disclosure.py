from live_nudges.app.disclosure import load_approved_offers_config, load_disclosures_config
from live_nudges.app.settings import Settings


def test_disclosures_config_loads_expected_keys():
    settings = Settings()
    config = load_disclosures_config(settings.disclosures_config_path_abs())
    assert "disclosure_phrases" in config
    assert "stage_trigger_phrases" in config
    assert "risky_phrases" in config
    assert "guaranteed returns" in config["risky_phrases"]


def test_approved_offers_config_loads_expected_shape():
    settings = Settings()
    config = load_approved_offers_config(settings.approved_offers_config_path_abs())
    assert "offers" in config
    topics = {offer["topic"] for offer in config["offers"]}
    assert "cross_sell:family_floater" in topics
    family_floater = next(o for o in config["offers"] if o["topic"] == "cross_sell:family_floater")
    assert "spouse" in family_floater["customer_trigger_phrases"]
    assert "family floater" in family_floater["agent_offer_phrases"]

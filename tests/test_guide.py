from src.domain.guide import OK_STATUS, load_offer_rows, load_pages_by_id


def test_offer_rows_carry_the_quality_status():
    rows = load_offer_rows()
    assert rows
    assert all("Offre_ID" in row and "Statut_qualité" in row for row in rows)
    assert any(row["Statut_qualité"] == OK_STATUS for row in rows)


def test_pages_by_id_maps_the_medecine_offers():
    pages = load_pages_by_id()
    assert pages["PUB-062"] == "36"
    assert pages["PUB-133"] == "47"

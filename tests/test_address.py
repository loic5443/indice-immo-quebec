import unittest

from domain.address import AddressValidationError, normalize_address
from services.address_form_service import restore_address_form, serialize_address_form, submit_address_form
from services.address_lookup_service import lookup
from components.property_analysis import prepare_address_submission


class AddressTests(unittest.TestCase):
    def test_full_map_style_address_regression(self):
        address = normalize_address("123 rue Exemple, Ville-exemple, QC, Canada", "Ville-exemple", "H2X1Y4")
        self.assertEqual(address.street, "123 rue Exemple")
        self.assertEqual(address.city, "Ville-exemple")
        self.assertEqual(address.postal_code, "H2X 1Y4")
        self.assertIn("Ville-exemple, QC, Canada", address.original_street)

    def test_interface_submission_normalizes_before_rerun(self):
        state = prepare_address_submission("123 rue Exemple, Ville-exemple, QC, Canada", "Ville-exemple", "H2X1Y4", consent=True)
        self.assertTrue(state.valid)
        self.assertEqual(state.values["postal"], "H2X 1Y4")
        self.assertEqual(state.address.street, "123 rue Exemple")

    def test_map_style_address_variants(self):
        self.assertEqual(normalize_address("123 rue Exemple, Ville-exemple, Québec, Canada", "Ville-exemple", "H2X1Y4").street, "123 rue Exemple")
        self.assertEqual(normalize_address("123 rue Exemple, Ville-exemple, QC, H2X 1Y4, Canada", "Ville-exemple", "").postal_code, "H2X 1Y4")
        self.assertEqual(normalize_address("123 rue Exemple, Ville-exemple, Quebec, Canada", "Ville-exemple", "H2X1Y4").city, "Ville-exemple")

    def test_map_city_conflict_is_precise(self):
        with self.assertRaises(AddressValidationError) as caught:
            normalize_address("123 rue Exemple, Ville-exemple, QC, Canada", "Montréal", "H2X1Y4")
        self.assertEqual(caught.exception.field, "city")

    def test_founder_reported_format_is_accepted(self):
        address = normalize_address(" 123, chemin de l’Église–Nord ", "Sainte-Marthe-sur-le-Lac", "j6n0a4")
        self.assertEqual(address.postal_code, "J6N 0A4")
        self.assertEqual(address.city, "Sainte-Marthe-sur-le-Lac")
        self.assertIn("Église", address.street)

    def test_postal_with_or_without_space(self):
        self.assertEqual(normalize_address("12 rue du Port", "L'Île-Cadieux", "H2X 1Y4").postal_code, "H2X 1Y4")
        self.assertEqual(normalize_address("12 rue du Port", "L'Île-Cadieux", "h2x1y4").postal_code, "H2X 1Y4")

    def test_missing_postal_is_allowed_only_for_a_role_backed_selection(self):
        self.assertFalse(submit_address_form("123 rue Exemple", "Ville-exemple", "", consent=True).valid)
        state = submit_address_form(
            "123 rue Exemple", "Ville-exemple", "", consent=True,
            allow_missing_postal=True,
            metadata={"official_source": "role", "postal_optional": True},
        )
        self.assertTrue(state.valid)
        self.assertEqual(state.address.postal_code, "")
        restored = restore_address_form(serialize_address_form(state))
        self.assertTrue(restored.valid)
        self.assertEqual(restored.metadata["official_source"], "role")

    def test_unicode_apostrophes_hyphens_unit_and_spaces(self):
        address = normalize_address("  12–14  rue  d’Argenson  ", "  Saint-Jean-sur-Richelieu ", "J6N 0A4", "  Apt.  3-B  ")
        self.assertEqual(address.unit, "Apt. 3-B")
        self.assertEqual(address.original_city, "Saint-Jean-sur-Richelieu")
        self.assertNotEqual(address.normalized_city, address.city)

    def test_precise_errors_and_boundaries(self):
        for values, field in [
            (("rue Sans Numéro", "Montréal", "H2X1Y4"), "street"),
            (("12 rue Test", "@@@", "H2X1Y4"), "city"),
            (("12 rue Test", "Montréal", "D2X1Y4"), "postal"),
        ]:
            with self.assertRaises(AddressValidationError) as caught:
                normalize_address(*values)
            self.assertEqual(caught.exception.field, field)
        with self.assertRaises(AddressValidationError):
            normalize_address("1 " + "rue" * 60, "Montréal", "H2X1Y4")

    def test_consent_and_manual_mode_do_not_transmit_address(self):
        address = normalize_address("123 rue Test", "Montréal", "H2X1Y4")
        self.assertEqual(lookup(address, False)["status"], "manual")

from django.test import TestCase
from unittest.mock import MagicMock, patch
from pid_provider.models import PidProviderXML


class PidProviderXMLBestMatchesTests(TestCase):

    def setUp(self):
        # xml_adapter_data é o dado já processado (ex.: xml_adapter.get_data_to_compare()),
        # e é passado direto para compare() -- não precisa simular atributos internos.
        self.xml_adapter_data_mock = {"title": "Titulo Original", "z_surnames": "Silva; Santos"}

    @patch("pid_provider.models.compare")
    def test_get_best_match_single_match_does_not_expose_matched_key(self, mock_compare):
        """Com apenas 1 item aprovado (>0.6), 'registered' deve existir mas 'matched' NÃO deve ser exposto."""

        item_bom = MagicMock(spec=PidProviderXML)
        item_bom.id = 101
        item_bom.updated.isoformat.return_value = "2026-06-27T12:00:00"
        item_bom.data_to_compare = {"title": "Titulo Original", "z_surnames": "Silva; Santos"}
        item_bom.data = {"id": 101, "title": "Titulo Original", "z_surnames": "Silva; Santos"}

        item_ruim = MagicMock(spec=PidProviderXML)
        item_ruim.id = 102
        item_ruim.updated.isoformat.return_value = "2026-06-27T13:00:00"
        item_ruim.data_to_compare = {"title": "Outro Titulo Completamente Diferente", "z_surnames": "Alves"}
        item_ruim.data = {"id": 102, "title": "Outro Titulo Completamente Diferente", "z_surnames": "Alves"}

        def side_effect_compare(item_data, xml_adapter_data):
            if item_data["title"] == "Titulo Original":
                return {"percentual_score": 0.95}
            return {"percentual_score": 0.20}

        mock_compare.side_effect = side_effect_compare

        # Enviados fora de ordem propositalmente
        candidates = [item_ruim, item_bom]
        result = PidProviderXML.get_best_match(candidates, self.xml_adapter_data_mock)

        # Apenas 1 item passou do corte -> "matched" não deve aparecer
        self.assertNotIn("matched", result)

        # "registered" deve existir e ser o OBJETO item de maior score
        self.assertEqual(result["registered"], item_bom)

        # "unmatched" sempre é exposto
        self.assertEqual(len(result["unmatched"]), 1)
        self.assertEqual(result["unmatched"][0]["id"], 102)

    @patch("pid_provider.models.compare")
    def test_get_best_match_no_candidates_approved(self, mock_compare):
        """Quando nenhum candidato atinge score > 0.6, nem 'registered' nem 'matched' devem existir."""

        item_fraco = MagicMock(spec=PidProviderXML)
        item_fraco.id = 201
        item_fraco.updated.isoformat.return_value = "2026-06-27T14:00:00"
        item_fraco.data_to_compare = {"title": "Quase igual, mas nao o suficiente"}
        item_fraco.data = {"id": 201, "title": "Quase igual, mas nao o suficiente"}

        mock_compare.return_value = {"percentual_score": 0.48}

        result = PidProviderXML.get_best_match([item_fraco], self.xml_adapter_data_mock)

        self.assertNotIn("registered", result)
        self.assertNotIn("matched", result)
        self.assertEqual(len(result["unmatched"]), 1)
        self.assertEqual(result["unmatched"][0]["id"], 201)

    @patch("pid_provider.models.compare")
    def test_get_best_match_two_matches_excludes_registered_from_matched(self, mock_compare):
        """Com 2 itens aprovados, 'registered' recebe o de maior score e 'matched' deve conter só o restante (matched[1:])."""

        item_antigo = MagicMock(spec=PidProviderXML)
        item_antigo.id = 301
        item_antigo.updated.isoformat.return_value = "2026-01-01T00:00:00"
        item_antigo.data_to_compare = {"title": "Clone"}
        item_antigo.data = {"id": 301, "title": "Clone"}

        item_recente = MagicMock(spec=PidProviderXML)
        item_recente.id = 302
        item_recente.updated.isoformat.return_value = "2026-06-27T00:00:00"  # Mais recente
        item_recente.data_to_compare = {"title": "Clone"}
        item_recente.data = {"id": 302, "title": "Clone"}

        # Mesmo score alto para os dois -> desempate por 'updated'
        mock_compare.return_value = {"percentual_score": 0.90}

        result = PidProviderXML.get_best_match([item_antigo, item_recente], self.xml_adapter_data_mock)

        # reverse=True em (score, updated.isoformat(), id);
        # "2026-06-27..." > "2026-01-01..." lexicograficamente, então item_recente vem primeiro (registered).
        self.assertEqual(result["registered"], item_recente)

        # "matched" agora é matched[1:] -> exclui o item que virou "registered"
        self.assertIn("matched", result)
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(result["matched"][0]["id"], 301)

        self.assertNotIn("unmatched", result)

    @patch("pid_provider.models.compare")
    def test_get_best_match_three_matches_only_secondary_items_in_matched(self, mock_compare):
        """Com 3+ itens aprovados, 'registered' fica com o 1º colocado e 'matched' com os demais, na mesma ordem de score."""

        item_1 = MagicMock(spec=PidProviderXML)
        item_1.id = 401
        item_1.updated.isoformat.return_value = "2026-06-01T00:00:00"
        item_1.data_to_compare = {"title": "A"}
        item_1.data = {"id": 401, "title": "A"}

        item_2 = MagicMock(spec=PidProviderXML)
        item_2.id = 402
        item_2.updated.isoformat.return_value = "2026-06-01T00:00:00"
        item_2.data_to_compare = {"title": "B"}
        item_2.data = {"id": 402, "title": "B"}

        item_3 = MagicMock(spec=PidProviderXML)
        item_3.id = 403
        item_3.updated.isoformat.return_value = "2026-06-01T00:00:00"
        item_3.data_to_compare = {"title": "C"}
        item_3.data = {"id": 403, "title": "C"}

        def side_effect_compare(item_data, xml_adapter_data):
            scores = {"A": 0.95, "B": 0.85, "C": 0.75}
            return {"percentual_score": scores[item_data["title"]]}

        mock_compare.side_effect = side_effect_compare

        result = PidProviderXML.get_best_match([item_3, item_1, item_2], self.xml_adapter_data_mock)

        # item_1 (0.95) é o de maior score -> vira "registered" e some da lista "matched"
        self.assertEqual(result["registered"], item_1)

        # "matched" deve conter apenas item_2 (0.85) e item_3 (0.75), nessa ordem
        self.assertEqual(len(result["matched"]), 2)
        self.assertEqual(result["matched"][0]["id"], 402)
        self.assertEqual(result["matched"][1]["id"], 403)

        self.assertNotIn("unmatched", result)
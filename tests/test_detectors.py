import unittest

from src.detectors import (
    load_nlp_model,
    detect_emails,
    detect_phones,
    detect_ssns,
    detect_credit_cards,
    detect_ipv4,
    detect_dobs,
    detect_ner,
    is_valid_person_candidate,
    is_valid_company_candidate
)


LOCATION = {
    "type": "paragraph",
    "index": 0
}


class TestPIIDetectors(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nlp = load_nlp_model()

    def test_email_detection(self):
        text = "Contact us at test.user@example.com for assistance."

        results = detect_emails(
            text,
            LOCATION
        )

        self.assertEqual(
            len(results),
            1
        )

        self.assertEqual(
            results[0]["text"],
            "test.user@example.com"
        )

        self.assertEqual(
            results[0]["type"],
            "EMAIL"
        )

    def test_phone_detection(self):
        text = "Please call 9876543210 for assistance."

        results = detect_phones(
            text,
            LOCATION
        )

        self.assertEqual(
            len(results),
            1
        )

        self.assertEqual(
            results[0]["text"],
            "9876543210"
        )

        self.assertEqual(
            results[0]["type"],
            "PHONE"
        )

    def test_ssn_detection(self):
        text = "SSN: 123-45-6789"

        results = detect_ssns(
            text,
            LOCATION
        )

        self.assertEqual(
            len(results),
            1
        )

        self.assertEqual(
            results[0]["text"],
            "123-45-6789"
        )

        self.assertEqual(
            results[0]["type"],
            "SSN"
        )

    def test_credit_card_detection(self):
        text = "Card number: 4111 1111 1111 1111"

        results = detect_credit_cards(
            text,
            LOCATION
        )

        self.assertEqual(
            len(results),
            1
        )

        self.assertEqual(
            results[0]["text"],
            "4111 1111 1111 1111"
        )

        self.assertEqual(
            results[0]["type"],
            "CREDIT_CARD"
        )

    def test_invalid_credit_card_is_rejected(self):
        text = "Invalid card: 1234 5678 9012 3456"

        results = detect_credit_cards(
            text,
            LOCATION
        )

        self.assertEqual(
            len(results),
            0
        )

    def test_ipv4_detection(self):
        text = "Server IP address: 192.168.1.10"

        results = detect_ipv4(
            text,
            LOCATION
        )

        self.assertEqual(
            len(results),
            1
        )

        self.assertEqual(
            results[0]["text"],
            "192.168.1.10"
        )

        self.assertEqual(
            results[0]["type"],
            "IP_ADDRESS"
        )

    def test_invalid_ipv4_is_rejected(self):
        text = "Invalid IP: 999.999.999.999"

        results = detect_ipv4(
            text,
            LOCATION
        )

        self.assertEqual(
            len(results),
            0
        )

    def test_date_of_birth_detection(self):
        text = "Date of Birth: 15 January 1990"

        results = detect_dobs(
            text,
            LOCATION
        )

        self.assertEqual(
            len(results),
            1
        )

        self.assertEqual(
            results[0]["text"],
            "15 January 1990"
        )

        self.assertEqual(
            results[0]["type"],
            "DATE_OF_BIRTH"
        )

    def test_person_detection(self):
        text = (
            "The director Sarthak Malvadkar "
            "attended the meeting."
        )

        results = detect_ner(
            text,
            LOCATION,
            self.nlp
        )

        person_results = [
            result
            for result in results
            if result["type"] == "PERSON"
        ]

        self.assertTrue(
            any(
                "Sarthak Malvadkar" in result["text"]
                for result in person_results
            )
        )

    def test_person_false_positive_is_rejected(self):
        self.assertFalse(
            is_valid_person_candidate("Offer")
        )

        self.assertFalse(
            is_valid_person_candidate("Reference Rate")
        )

        self.assertFalse(
            is_valid_person_candidate("Registered Office")
        )

        self.assertFalse(
            is_valid_person_candidate("Baner")
        )

    def test_valid_person_candidate(self):
        self.assertTrue(
            is_valid_person_candidate(
                "Sarthak Malvadkar"
            )
        )

        self.assertTrue(
            is_valid_person_candidate(
                "Kushal Subbayya Hegde"
            )
        )

    def test_company_detection(self):
        text = (
            "KSH International Limited "
            "is the company mentioned in the document."
        )

        results = detect_ner(
            text,
            LOCATION,
            self.nlp
        )

        company_results = [
            result
            for result in results
            if result["type"] == "COMPANY"
        ]

        self.assertTrue(
            any(
                "KSH International Limited"
                in result["text"]
                for result in company_results
            )
        )

    def test_company_false_positive_is_rejected(self):
        self.assertFalse(
            is_valid_company_candidate(
                "Offer"
            )
        )

        self.assertFalse(
            is_valid_company_candidate(
                "Registered Office"
            )
        )

        self.assertFalse(
            is_valid_company_candidate(
                "Anchor Investors"
            )
        )

    def test_valid_company_candidate(self):
        self.assertTrue(
            is_valid_company_candidate(
                "KSH International Limited"
            )
        )

        self.assertTrue(
            is_valid_company_candidate(
                "Bhandary Metal Extrusion Private Limited"
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
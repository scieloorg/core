from argon2.low_level import Type, hash_secret_raw
from django.test import SimpleTestCase

from core.utils.bunny_shield import _accepted, solve


class BunnyShieldTest(SimpleTestCase):
    def test_difficulty_mask_matches_the_worker_script(self):
        self.assertTrue(_accepted("00ab", 13))
        self.assertFalse(_accepted("01ab", 13))
        self.assertFalse(_accepted("10ab", 13))
        self.assertTrue(_accepted("0cab", 10))
        self.assertFalse(_accepted("01ab", 10))

    def test_solver_returns_an_accepted_counter(self):
        token = "userkey1#challenge#1794522559#signature"
        answer = solve(token, difficulty=8)
        counter = answer.rsplit("#", 1)[-1]
        digest = hash_secret_raw(
            secret=f"challenge{counter}".encode(),
            salt=b"userkey1",
            time_cost=2,
            memory_cost=512,
            parallelism=1,
            hash_len=32,
            type=Type.ID,
        ).hex()

        self.assertTrue(answer.startswith(f"{token}#"))
        self.assertTrue(_accepted(digest, 8))

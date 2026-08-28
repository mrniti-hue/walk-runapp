from app.services.passkey import generate_passkey, hash_passkey, verify_passkey


def test_generated_passkey_uses_unambiguous_alphabet():
    passkey = generate_passkey()
    assert len(passkey) == 10
    for ch in "0O1IL":
        assert ch not in passkey


def test_verify_accepts_correct_passkey():
    passkey = generate_passkey()
    assert verify_passkey(passkey, hash_passkey(passkey))


def test_verify_rejects_wrong_passkey():
    assert not verify_passkey("WRONGCODE1", hash_passkey(generate_passkey()))


def test_hash_is_case_and_whitespace_insensitive():
    assert hash_passkey(" abc123 ") == hash_passkey("ABC123")

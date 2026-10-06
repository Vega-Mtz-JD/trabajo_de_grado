"""Pruebas del núcleo criptográfico (caja blanca)."""

import itertools
import secrets

import pytest

from votoseguro.cripto import cifrado_voto as cv
from votoseguro.cripto import firmas, shamir
from votoseguro.cripto.hashing import canonico, hash_canonico, sha3
from votoseguro.cripto.merkle import raiz_merkle

ELECCION = "6f1c0a3e-0000-4000-8000-000000000001"


@pytest.fixture(scope="module")
def clave_eleccion():
    # 2048 bits en pruebas para que sean rápidas; en producción se usan 3072.
    return cv.generar_clave_eleccion(2048)


@pytest.fixture(scope="module")
def clave_firma():
    return firmas.generar_clave_firma()


# --- hashing -------------------------------------------------------------------------------

def test_sha3_vector_conocido():
    # Vector oficial NIST de SHA3-256 para "abc"
    assert sha3(b"abc") == "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532"


def test_canonico_es_independiente_del_orden_de_claves():
    assert canonico({"b": 1, "a": [1, 2]}) == canonico({"a": [1, 2], "b": 1})
    assert hash_canonico({"x": "ñ"}) == hash_canonico({"x": "ñ"})


def test_canonico_rechaza_flotantes():
    with pytest.raises(TypeError):
        canonico({"total": 1.5})


# --- Merkle --------------------------------------------------------------------------------

def _hashes(n):
    return [sha3(secrets.token_bytes(16)) for _ in range(n)]


def test_merkle_no_depende_del_orden():
    hs = _hashes(7)
    assert raiz_merkle(hs) == raiz_merkle(list(reversed(hs)))


@pytest.mark.parametrize("n", [1, 2, 3, 8, 13])
def test_merkle_detecta_alteracion_insercion_y_eliminacion(n):
    hs = _hashes(n)
    raiz = raiz_merkle(hs)
    alterado = hs.copy()
    alterado[0] = sha3(b"otro voto")
    assert raiz_merkle(alterado) != raiz
    assert raiz_merkle(hs + _hashes(1)) != raiz
    if n > 1:
        assert raiz_merkle(hs[1:]) != raiz


def test_merkle_vacio_y_duplicados():
    assert raiz_merkle([]) == sha3(b"")
    h = _hashes(1)[0]
    with pytest.raises(ValueError):
        raiz_merkle([h, h])


def test_merkle_hoja_unica_no_es_el_hash_mismo():
    # Por el prefijo de dominio, la raíz de una hoja no coincide con la hoja.
    h = _hashes(1)[0]
    assert raiz_merkle([h]) != h


# --- Shamir --------------------------------------------------------------------------------

def test_shamir_cualquier_combinacion_de_umbral_reconstruye():
    secreto = secrets.token_bytes(32)
    partes = shamir.dividir(secreto, umbral=3, partes=5)
    for combinacion in itertools.combinations(partes, 3):
        assert shamir.combinar(list(combinacion)) == secreto
    assert shamir.combinar(partes) == secreto  # más partes que el umbral también sirve


def test_shamir_menos_partes_que_el_umbral_no_revela_el_secreto():
    secreto = secrets.token_bytes(32)
    partes = shamir.dividir(secreto, umbral=3, partes=5)
    for combinacion in itertools.combinations(partes, 2):
        assert shamir.combinar(list(combinacion)) != secreto


def test_shamir_texto_ida_y_vuelta_y_error_de_tipeo():
    parte = shamir.dividir(b"secreto", 2, 3)[1]
    texto = parte.a_texto()
    assert shamir.Parte.desde_texto(texto) == parte
    ultimo = texto[-1]
    with pytest.raises(ValueError, match="verificación"):
        shamir.Parte.desde_texto(texto[:-1] + ("0" if ultimo != "0" else "1"))
    with pytest.raises(ValueError):
        shamir.Parte.desde_texto("basura")


@pytest.mark.parametrize("umbral,partes", [(1, 3), (4, 3), (2, 256)])
def test_shamir_parametros_invalidos(umbral, partes):
    with pytest.raises(ValueError):
        shamir.dividir(b"x", umbral, partes)


def test_shamir_partes_repetidas():
    p = shamir.dividir(b"x", 2, 3)
    with pytest.raises(ValueError):
        shamir.combinar([p[0], p[0]])


# --- Cifrado de votos ----------------------------------------------------------------------

def test_voto_ida_y_vuelta(clave_eleccion):
    cifrado = cv.cifrar_voto(clave_eleccion.public_key(), ELECCION, b"FRENTE-A")
    assert cv.descifrar_voto(clave_eleccion, ELECCION, cifrado) == b"FRENTE-A"


def test_votos_tienen_longitud_fija_y_son_no_deterministas(clave_eleccion):
    pub = clave_eleccion.public_key()
    a = cv.cifrar_voto(pub, ELECCION, b"A")
    b = cv.cifrar_voto(pub, ELECCION, b"OPCION-CON-NOMBRE-MUCHO-MAS-LARGO")
    c = cv.cifrar_voto(pub, ELECCION, b"A")
    assert len(a) == len(b) == len(c)  # la longitud no revela la opción
    assert a != c                      # mismo voto, distinto texto cifrado


def test_voto_alterado_o_de_otra_eleccion_se_rechaza(clave_eleccion):
    cifrado = bytearray(cv.cifrar_voto(clave_eleccion.public_key(), ELECCION, b"A"))
    with pytest.raises(cv.ErrorDescifrado):
        cv.descifrar_voto(clave_eleccion, "otra-eleccion", bytes(cifrado))
    cifrado[-1] ^= 0x01
    with pytest.raises(cv.ErrorDescifrado):
        cv.descifrar_voto(clave_eleccion, ELECCION, bytes(cifrado))
    with pytest.raises(cv.ErrorDescifrado):
        cv.descifrar_voto(clave_eleccion, ELECCION, bytes(cifrado[:-1]))


def test_contenido_demasiado_largo(clave_eleccion):
    with pytest.raises(ValueError):
        cv.cifrar_voto(clave_eleccion.public_key(), ELECCION, b"x" * cv.TAMANIO_CONTENIDO)


def test_custodia_umbral_3_de_5(clave_eleccion):
    cifrada, partes = cv.custodiar_clave(clave_eleccion, umbral=3, partes=5)
    voto = cv.cifrar_voto(clave_eleccion.public_key(), ELECCION, b"B")
    recuperada = cv.recuperar_clave(cifrada, [partes[4], partes[0], partes[2]])
    assert cv.descifrar_voto(recuperada, ELECCION, voto) == b"B"
    with pytest.raises(cv.ErrorDescifrado):
        cv.recuperar_clave(cifrada, partes[:2])


def test_publica_pem_ida_y_vuelta(clave_eleccion):
    pub = clave_eleccion.public_key()
    assert cv.publica_desde_pem(cv.publica_a_pem(pub)).public_numbers() == pub.public_numbers()


# --- Firmas --------------------------------------------------------------------------------

def test_firma_valida_y_alterada(clave_firma):
    acta = canonico({"total": 100, "opciones": {"A": 60, "B": 40}})
    firma = firmas.firmar(clave_firma, acta)
    pub = clave_firma.public_key()
    assert firmas.verificar(pub, acta, firma)
    assert not firmas.verificar(pub, acta.replace(b"60", b"61"), firma)
    otra = firmas.generar_clave_firma()
    assert not firmas.verificar(otra.public_key(), acta, firma)


def test_clave_privada_cifrada_con_frase(clave_firma):
    pem = firmas.privada_a_pem(clave_firma, b"frase-de-paso-larga")
    assert b"ENCRYPTED" in pem
    recuperada = firmas.privada_desde_pem(pem, b"frase-de-paso-larga")
    assert firmas.huella(recuperada.public_key()) == firmas.huella(clave_firma.public_key())
    with pytest.raises(ValueError):
        firmas.privada_desde_pem(pem, b"frase-incorrecta!!")
    with pytest.raises(ValueError):
        firmas.privada_a_pem(clave_firma, b"corta")

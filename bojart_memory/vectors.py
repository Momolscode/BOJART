import math


def validate_vector(vector):
    if not isinstance(vector, list) or not vector or len(vector) > 8192:
        raise ValueError('Vecteur invalide.')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in vector) or not any(vector):
        raise ValueError('Valeurs du vecteur invalides.')


def cosine(a, b):
    validate_vector(a); validate_vector(b)
    if len(a) != len(b):
        raise ValueError('Dimensions incompatibles : réindexer avec le même modèle.')
    return sum(x*y for x, y in zip(a, b)) / math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))

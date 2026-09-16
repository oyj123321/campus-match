"""Self-reported age and mutual, optional age limits (inclusive)."""

MIN_AGE = 18
MAX_AGE = 100


def apply_age_fields(user, data, required=False):
    """Validate before mutating. Return an error key, or None."""
    values = {}
    for key in ('age', 'preferred_age_min', 'preferred_age_max'):
        raw = data.get(key, getattr(user, key, None))
        if raw is None or raw == '':
            values[key] = None
        elif type(raw) is not int or not MIN_AGE <= raw <= MAX_AGE:
            return 'age.invalid'
        else:
            values[key] = raw
    age, low, high = (values[k] for k in ('age', 'preferred_age_min', 'preferred_age_max'))
    if required and age is None:
        return 'age.required'
    if age is None and (low is not None or high is not None):
        return 'age.needOwn'
    if (low is None) != (high is None) or (low is not None and low > high):
        return 'age.rangeInvalid'
    for key, value in values.items():
        setattr(user, key, value)
    if any(key in data for key in values):
        from datetime import datetime
        user.age_confirmed_at = datetime.utcnow() if age is not None else None
    return None


def age_compatible(a, b):
    for owner, other in ((a, b), (b, a)):
        low = getattr(owner, 'preferred_age_min', None)
        high = getattr(owner, 'preferred_age_max', None)
        if low is None and high is None:
            continue
        own_age = getattr(owner, 'age', None)
        age = getattr(other, 'age', None)
        if own_age is None or age is None or low is None or high is None:
            return False
        if not low <= age <= high:
            return False
    return True

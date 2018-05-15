import hashlib

def hash_func(user):# {{{
    salt = 'aksdjocijnewqkjdcis893sa'
    func = hashlib.sha512()
    func.update((user + salt).encode(encoding='utf-8'))
    return func.hexdigest()
# }}}

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

from sonyflake import SonyFlake

gen = SonyFlake()

def encode_base62(num):
    if num == 0:
        return "0"

    result = []

    while num:
        num, rem = divmod(num, 62)
        result.append(ALPHABET[rem])

    return ''.join(reversed(result))

for i in range(1000):
    print(encode_base62(gen.next_id()))


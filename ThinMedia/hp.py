import codecs

def encode_string(string):
    if not string:
        return ""
    return codecs.encode(bytes(string, 'utf-8'), "hex").decode('utf-8')

def decode_string(string):
    if not string:
        return ""
    return codecs.decode(bytes(string, 'utf-8'), "hex").decode('utf-8')

def decode_string_list(strings: list):
    if not strings:
        return []
    return [codecs.decode(bytes(i, 'utf-8'), "hex").decode('utf-8') for i in strings]

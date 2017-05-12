#
# Script intended to ease malicious JS deobfuscation.
#
# Deobfuscates Locky Javascript transformations to a human readable JS
#   (most likely it will work with other malware obfuscation transformations as well)
#
# Try this out with:
#   $ python translate.py -f locky.js -s deobfuscate.py Deobfuscate
#
#   https://gist.github.com/mgeeky/8cfed1d6f9fb320587b3207438d25e66

import re


def Deobfuscate(data):

        # Rule 1: Unescape unicode.
    out = re.sub(r"\\u(0*[0-9a-f]{2})", lambda x: chr(int(x.group(1), 16)), data, flags=re.I | re.M)

    # Rule 2: Delete comment lines.
    out = re.sub(r"^\s*//.+\n?", "", out, flags=re.M)

    # Rule 3: Split lines by semicolon.
    out = re.sub(r";(?<!\n)", ";\n", out)

    # Rule 4: Concatenate last element from a list to the following element.
    out = re.sub(r"\((?:['\"][^\"']+['\"],)+([\"'][^\"']+[\"'])\)", r"\1", out, flags=re.I)

    # Rule 5: Concatenate adjacent strings
    prev = ''
    while (prev != out):
        prev = out
        out = re.sub(r"(?:\B([\"'][^'\"]+)[\"']\B)\+(?:\B[\"']([^'\"]+[\"'])\B)",
                     r"\1\2", prev, flags=re.I)

        # Rule 6: Substitute string indexes in associative dereferencing.
        for m in re.finditer(r"([ \t]*(?:var)?\s*)(?<!\.)\b([^'\"\s\.]+)(\s*=\s*)((?:'[^']+')|(?:\"[^\"]+\"))(\s*;?.*)", out, flags=re.I | re.M):
            found = m.group(1) + m.group(4) + m.group(3) + m.group(4) + m.group(5)
            out = re.sub(r"\b" + m.group(2) + r"\b", m.group(4), out)
            out = out.replace(found, '')
            pass

    # Rule 7: Convert javascript associative members access into dereference ones
    out = re.sub("(\w+)\[['\"](\w+)['\"]\]", r"\1.\2", out, flags=re.M)

    # Rule 8: Remove empty lines
    out = '\n'.join(filter(lambda x: not re.match(r'^\s*$', x), out.split('\n')))

    # Rule 9: Rename used variables
    ctr = 1
    for m in re.finditer(r"([ \t]*(?:var)?\s*)(?<!\.)\b([^'\"\s\.]+)(\s*=)", out, flags=re.I | re.M):
        out = out.replace(m.group(2), 'variable_%d' % ctr)
        ctr += 1

    # Rule 10: Simple beautifying.
    out = re.sub(r"([^\n\{]+\{)", r"\n\1", out)

    return out

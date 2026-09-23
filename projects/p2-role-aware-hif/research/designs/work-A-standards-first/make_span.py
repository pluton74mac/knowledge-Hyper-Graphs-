"""Build the source text behind evidence f1/e2 and patch the fixture with its true digest and offsets (F11).

Offsets are Unicode code points, half-open, over the NFC text; the digest is sha256 of the NFC text in UTF-8.
The text contains U+1F48A (a non-BMP character) before the span, so code-point offsets differ from
UTF-16 offsets (JavaScript) and from UTF-8 byte offsets; the check below shows all three.
"""
import hashlib
import json
import os
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
head = ("Guideline excerpt (Zürich edition) \U0001F48A: for adults with type 2 diabetes, clinicians "
        "should consider metformin first-line unless contraindicated; titrate slowly, review renal "
        "function and ")
text = head + "start with 500 mg metformin twice daily, with meals."
text = unicodedata.normalize("NFC", text)
exact = "500 mg metformin"
start = text.index(exact)
end = start + len(exact)
prefix, suffix = text[start - 11:start], text[end:end + 12]
digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
utf16_start = len(text[:start].encode("utf-16-le")) // 2
utf8_start = len(text[:start].encode("utf-8"))
assert text[start:end] == exact and prefix == "start with " and suffix == " twice daily"
with open(os.path.join(HERE, "doc-pmid-0000001.txt"), "w", encoding="utf-8") as f:
    f.write(text)
p = os.path.join(HERE, "gate-fixture.khg.json")
doc = json.load(open(p, encoding="utf-8"))
for e in doc["edges"]:
    if e["edge"] == "f1":
        for ev in e["evidence"]:
            if ev["id"] == "e2":
                ev.update({"digest": digest, "start": start, "end": end, "prefix": prefix, "suffix": suffix})
with open(p, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)
    f.write("\n")
print(json.dumps({"code_point_start": start, "end": end, "utf16_start": utf16_start, "utf8_byte_start": utf8_start,
                  "digest": digest, "len_code_points": len(text)}, indent=1))

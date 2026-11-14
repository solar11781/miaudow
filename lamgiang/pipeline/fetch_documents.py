"""Fetch public Vietnamese legal texts for the MIAUDOW evidence library (Core 02) and chunk them by Điều and khoản.

Documents
  qd18_2021  QĐ 18/2021/QĐ-TTg (source_id R-A01): Word file on the Viet Nam Disaster Prevention portal of the Ministry
             of Agriculture and Environment, https://vupc.mae.gov.vn/Data/files/18_2021_QD-TTg.doc, converted with
             antiword (UTF-8). Articles 1-63 of the body are chunked; the annexes (tables) are not.
  nd112_2024 NĐ 112/2024/NĐ-CP (source_id R-G06): full text published on the National Database of Legal Documents
             (Cơ sở dữ liệu quốc gia về pháp luật, Ministry of Justice), https://vbpl.vn, item 169866. Articles 1-20.
Copyright basis: Luật Sở hữu trí tuệ 50/2005/QH11, Điều 15 (texts are fetched from vbpl.vn and quoted in the manifest).

Wording is never changed: only HTML tags are removed and runs of spaces inside one paragraph are collapsed.
Downloads are cached in data/cache/documents/ (git-ignored).

Run:  .venv\\Scripts\\python.exe pipeline\\fetch_documents.py
"""

from __future__ import annotations

import hashlib
import html as htmlmod
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "MiaudowResearch/1.0 (NASA Space Apps 2026 hackathon)"
CACHE = ROOT / "data" / "cache" / "documents"
OUT = ROOT / "data" / "raw" / "documents"
VBPL = "https://vbpl.vn/van-ban/chi-tiet/"
LICENSE_LEGAL = (
    "Not protected by copyright: Luật Sở hữu trí tuệ 50/2005/QH11 (amended), Điều 15 khoản 2 - "
    "văn bản quy phạm pháp luật (https://vbpl.vn/van-ban/chi-tiet/luat-so-huu-tri-tue-so-50-2005-qh11--16748)"
)

DOCS = {
    "qd18_2021": {
        "source_id": "R-A01",
        "title": "Quyết định 18/2021/QĐ-TTg quy định về dự báo, cảnh báo, truyền tin thiên tai và cấp độ rủi ro thiên tai",
        "url": "https://vupc.mae.gov.vn/Data/files/18_2021_QD-TTg.doc",
        "kind": "doc",
        "keep_articles": (1, 63),
    },
    "nd112_2024": {
        "source_id": "R-G06",
        "title": "Nghị định 112/2024/NĐ-CP quy định chi tiết về đất trồng lúa",
        "url": VBPL + "nghi-dinh-so-112-2024-nd-cp-quy-dinh-chi-tiet-ve-dat-trong-lua--169866",
        "kind": "vbpl",
        "keep_articles": (1, 20),
    },
}
IP_LAW = {
    "law_2005": VBPL + "luat-so-huu-tri-tue-so-50-2005-qh11--16748",
    "amend_2025": VBPL + "luat-sua-doi-bo-sung-mot-so-dieu-cua-luat-so-huu-tri-tue-so-131-2025-qh15--187492",
}

ARTICLE_RE = re.compile(r"^Điều\s+(\d+)\s*\.\s*(.*)$")
CLAUSE_RE = re.compile(r"^(\d+)\.\s+\S")
STRUCT_RE = re.compile(r"^(Chương\s+[IVXLC]+\b|Mục\s+\d+\b)")
END_RE = re.compile(r"^(PHỤ LỤC|Phụ lục\s+[IVX]+\s*$|Nơi nhận\s*:|\|?\s*Nơi nhận)")


# ----------------------------------------------------------------------------------------------- pure functions
def html_to_paragraphs(fragment: str) -> list[str]:
    """Block-level HTML to plain paragraphs: tags removed, entities decoded, spaces collapsed, wording untouched."""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", fragment)
    s = re.sub(r"\s+", " ", s)  # newlines in HTML source are plain whitespace
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|table)>", "\n\n", s)
    s = re.sub(r"(?i)</t[dh]>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmlmod.unescape(s).replace("\xa0", " ")
    paras = []
    for block in re.split(r"\n\s*\n", s):
        lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in block.split("\n")]
        text = "\n".join(ln for ln in lines if ln)
        if text:
            paras.append(text)
    return paras


def text_to_paragraphs(text: str) -> list[str]:
    """antiword output: paragraphs separated by blank lines."""
    paras = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [ln.rstrip() for ln in block.split("\n")]
        t = "\n".join(ln for ln in lines if ln.strip()).strip()
        if t:
            paras.append(t)
    return paras


def chunk_by_article(paragraphs: list[str], keep: tuple[int, int] | None = None) -> list[dict]:
    """Split into chunks: one per khoản (numbered clause) of each Điều; text before the first khoản of an article
    (or an article without khoản) becomes a chunk located at the article itself. Points a), b) stay in their khoản.
    Stops at the first annex or 'Nơi nhận' block after the body has started. Returns dicts with location, heading,
    article, clause, chapter, text."""
    chunks: list[dict] = []
    chapter = ""  # "Chương I NHỮNG QUY ĐỊNH CHUNG"
    section = ""  # "Mục 1. ..."
    art: tuple[int, str] | None = None
    clause: int | None = None
    buf: list[str] = []
    started = False

    def label() -> str | None:
        return " / ".join(x for x in (chapter, section) if x) or None

    def flush() -> None:
        nonlocal buf
        if art is not None and buf:
            n, title = art
            if keep is None or keep[0] <= n <= keep[1]:
                loc = f"Điều {n}" if clause is None else f"Điều {n}, khoản {clause}"
                chunks.append(
                    {
                        "location": loc,
                        "heading": f"Điều {n}. {title}".strip(),
                        "article": n,
                        "clause": clause,
                        "chapter": label(),
                        "text": "\n".join(buf),
                    }
                )
        buf = []

    for p in paragraphs:
        first = p.split("\n", 1)[0].strip()
        if started and END_RE.match(first):
            break
        m = ARTICLE_RE.match(first)
        if m:
            flush()
            started = True
            art = (int(m.group(1)), m.group(2).strip())
            clause = None
            rest = p.split("\n", 1)[1].strip() if "\n" in p else ""
            if rest:
                buf.append(rest)
            continue
        if STRUCT_RE.match(first):
            flush()
            started = True
            art, clause = None, None
            if first.startswith("Chương"):
                chapter, section = " ".join(p.split()), ""
            else:
                section = " ".join(p.split())
            continue
        if art is None:
            # a chapter title on its own line right after "Chương I" (e.g. "NHỮNG QUY ĐỊNH CHUNG")
            if started and chapter and not section and p.upper() == p:
                chapter = f"{chapter} {' '.join(p.split())}"
            continue
        cm = CLAUSE_RE.match(first)
        if cm:
            flush()
            clause = int(cm.group(1))
        buf.append(p)
    flush()
    return chunks


def extract_next_payload(page_html: str) -> str:
    """Concatenate the Next.js flight payload strings of a vbpl.vn page."""
    parts = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', page_html, re.S)
    return "".join(json.loads(p) for p in parts)


def json_string_field(payload: str, key: str, must_contain: str | None = None) -> str | None:
    """First string value of `key` in the payload (optionally the first one containing `must_contain`)."""
    for m in re.finditer(r'"' + re.escape(key) + r'":("(?:[^"\\]|\\.)*")', payload):
        v = json.loads(m.group(1))
        if must_contain is None or must_contain in v:
            return v
    return None


def resolve_text_ref(payload: str, ref: str) -> str | None:
    """React flight text row '<id>:T<hex byte length>,<text>' referenced as '$<id>'."""
    rid = ref[1:] if ref.startswith("$") else ref
    m = re.search(r"(?:^|\n|\})" + re.escape(rid) + r":T([0-9a-fA-F]+),", payload)
    if not m:
        return None
    n = int(m.group(1), 16)
    return payload[m.end() :].encode("utf-8")[:n].decode("utf-8", errors="strict")


def vbpl_content(payload: str) -> str | None:
    """The document body HTML: documentContent.content, following a '$id' text reference when there is one."""
    m = re.search(r'"documentContent":\{"id":"[^"]*","title":[^,]*,"content":("(?:[^"\\]|\\.)*")', payload)
    if m:
        v = json.loads(m.group(1))
        if v.startswith("$"):
            return resolve_text_ref(payload, v)
        return v
    return json_string_field(payload, "documentContent", must_contain="<p")


def json_scalar_field(payload: str, key: str) -> str | None:
    m = re.search(r'"' + re.escape(key) + r'":("(?:[^"\\]|\\.)*"|[^,}\]]+)', payload)
    if not m:
        return None
    v = m.group(1)
    return json.loads(v) if v.startswith('"') else v


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ----------------------------------------------------------------------------------------------- I/O
def download(url: str, dest: Path, tries: int = 5) -> tuple[bytes, dict]:
    import httpx

    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    if dest.exists() and meta_path.exists():
        return dest.read_bytes(), json.loads(meta_path.read_text(encoding="utf-8"))
    delay = 5.0
    last = None
    for _ in range(tries):
        try:
            r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=180, follow_redirects=True)
            if r.status_code == 200:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                meta = {
                    "url": url,
                    "final_url": str(r.url),
                    "status": r.status_code,
                    "content_type": r.headers.get("content-type"),
                    "last_modified": r.headers.get("last-modified"),
                    "etag": r.headers.get("etag"),
                    "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
                return r.content, meta
            last = f"HTTP {r.status_code}"
            if r.status_code not in (429, 500, 502, 503, 504):
                break
        except httpx.HTTPError as exc:
            last = repr(exc)
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {last}")


def antiword_text(doc_path: Path) -> str:
    exe = shutil.which("antiword")
    if not exe:
        raise RuntimeError("antiword not found on PATH (Git for Windows ships it in /mingw64/bin)")
    out = subprocess.run([exe, "-m", "UTF-8.txt", "-w", "0", str(doc_path)], capture_output=True, check=True)
    return out.stdout.decode("utf-8")


def vbpl_document(url: str, dest: Path) -> tuple[str, dict, bytes]:
    raw, meta = download(url, dest)
    payload = extract_next_payload(raw.decode("utf-8"))
    content = vbpl_content(payload)
    if not content or "<" not in content:
        raise RuntimeError(f"no documentContent in {url}")
    info = {k: json_scalar_field(payload, k) for k in ("documentContentFileName", "documentContentFileDocName")}
    lf = re.search(r'"legislationLegalForce":"([^"]+)"', raw.decode("utf-8"))
    info["legislationLegalForce (schema.org on the page)"] = lf.group(1) if lf else None
    meta = {**meta, **{k: v for k, v in info.items() if v is not None}}
    return content, meta, raw


def article_text(paragraphs: list[str], number: int) -> str | None:
    chunks = [c for c in chunk_by_article(paragraphs) if c["article"] == number]
    if not chunks:
        return None
    return chunks[0]["heading"] + "\n" + "\n".join(c["text"] for c in chunks)


def verify_ip_law() -> dict:
    out = {}
    try:
        content, meta, _ = vbpl_document(IP_LAW["law_2005"], CACHE / "ip_law" / "luat_shtt_2005.html")
        out["law_2005"] = {
            "url": IP_LAW["law_2005"],
            "dieu_15": article_text(html_to_paragraphs(content), 15),
            "retrieved_at": meta.get("retrieved_at"),
        }
    except Exception as exc:  # noqa: BLE001
        out["law_2005"] = {"url": IP_LAW["law_2005"], "error": str(exc)}
    try:
        content, meta, _ = vbpl_document(IP_LAW["amend_2025"], CACHE / "ip_law" / "luat_shtt_sua_2025.html")
        paras = html_to_paragraphs(content)
        hits = []
        for i, p in enumerate(paras):
            if re.search(r"Điều 15\b", p):
                hits.append("\n".join(paras[i : i + 2]))  # the amending sentence and the inserted text
        out["amend_2025"] = {
            "url": IP_LAW["amend_2025"],
            "paragraphs_mentioning_dieu_15": hits[:5],
            "retrieved_at": meta.get("retrieved_at"),
            "reading": "The 2025 amendment adds a khoản 4 to Điều 15; khoản 2 is unchanged.",
        }
    except Exception as exc:  # noqa: BLE001
        out["amend_2025"] = {"url": IP_LAW["amend_2025"], "error": str(exc)}
    return out


P02 = {
    "doc_id": "p02",
    "source_id": "R-P02",
    "title": (
        "Trịnh Đức Toàn et al. (2023). Kết quả thử nghiệm một số cây trồng trên đất lúa kém hiệu quả, thường "
        "xuyên khô hạn tại tỉnh Nghệ An. Tạp chí Khoa học và Công nghệ Nông nghiệp Việt Nam 04(146): 43-51"
    ),
    "article_page": "https://vjol.info.vn/vaas/vi/article/view/167049",
    "galley": "https://vjol.info.vn/vaas/vi/article/download/167049/143292/289735",
    "journal_site_policy": "http://tapchivaas.vn/page/thong-tin-chung/quy-che-hoat-dong-140227",
}


def check_p02() -> dict:
    """Record what VJOL and the journal say about access and licence. The PDF is NOT downloaded or stored."""
    import httpx

    entry = {k: v for k, v in P02.items()}
    h = {"User-Agent": USER_AGENT}
    try:
        page = httpx.get(P02["article_page"], headers=h, timeout=60, follow_redirects=True).text
        title = re.search(r'<meta name="citation_title" content="([^"]*)"', page)
        entry["vjol_metadata_title_for_167049"] = title.group(1) if title else None
        entry["vjol_page_licence_statement"] = (
            "none found" if not re.search(r"creativecommons|giấy phép CC|license", page, re.I) else "see page"
        )
        time.sleep(1)
        pol = httpx.get(P02["journal_site_policy"], headers=h, timeout=60, follow_redirects=True).text
        m = re.search(r"©\s*Bản quyền[^<.]*\.\s*[^<.]*\.", re.sub(r"<[^>]+>", " ", pol))
        entry["journal_site_copyright_statement"] = " ".join(m.group(0).split()) if m else None
    except Exception as exc:  # noqa: BLE001
        entry["error"] = str(exc)
    entry.update(
        {
            "status": "RECORDED_ONLY",
            "license": (
                "No open licence found. VJOL serves the full text free of charge but states no reuse licence; the "
                "journal's own site says '© Bản quyền thuộc Tạp chí Viện Khoa học Nông nghiệp Việt Nam - VAAS. "
                "Không được phép sao chép khi chưa được chấp thuận bằng văn bản.' The PDF and its text are "
                "therefore not stored and no chunks are made."
            ),
            "manual_check_2026_11_14": (
                "The galley at the URL above (served as 'news-tap-chi-bài 8 số 4 năm 2023.pdf', 9 pages, sha256 "
                "1f96246f96b6d39086b0ea1d1c2e317d506ec49ee6ee404d4f02e8d3ca4b3bd0) holds printed pages 43-51 of issue "
                "04(146)/2023: the English abstract of the preceding paper (Vinh Linh pepper cuttings) and then the P-02 "
                "paper. VJOL's metadata for article 167049 carries a different title (a jackfruit disease paper). The "
                "PDF's text layer loses most Vietnamese letters with pdftotext (font without a Unicode map), so even a "
                "licensed copy would need OCR. The PDF was deleted after the check."
            ),
        }
    )
    return entry


def write_chunks(doc_id: str, spec: dict, chunks: list[dict], url: str, sha: str, retrieved_at: str) -> Path:
    d = OUT / doc_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / "chunks.jsonl"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for i, c in enumerate(chunks):
            rec = {
                "doc_id": doc_id,
                "source_id": spec["source_id"],
                "location": c["location"],
                "text": c["text"],
                "url": url,
                "license": LICENSE_LEGAL,
                "retrieved_at": retrieved_at,
                "sha256_of_source": sha,
                "chunk_id": f"{doc_id}-{i:04d}",
                "heading": c["heading"],
                "chapter": c["chapter"],
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest_docs = []
    for doc_id, spec in DOCS.items():
        entry = {"doc_id": doc_id, "source_id": spec["source_id"], "title": spec["title"], "source_url": spec["url"]}
        try:
            if spec["kind"] == "doc":
                raw, meta = download(spec["url"], CACHE / doc_id / Path(spec["url"]).name)
                text = antiword_text(CACHE / doc_id / Path(spec["url"]).name)
                (CACHE / doc_id / "antiword.txt").write_text(text, encoding="utf-8")
                paras = text_to_paragraphs(text)
                entry["extraction"] = "antiword -m UTF-8.txt -w 0 (Word 97-2003 .doc to UTF-8 text)"
            else:
                content, meta, raw = vbpl_document(spec["url"], CACHE / doc_id / "vbpl_page.html")
                (CACHE / doc_id / "document_content.html").write_text(content, encoding="utf-8")
                paras = html_to_paragraphs(content)
                entry["extraction"] = (
                    "documentContent HTML from the vbpl.vn page payload; tags removed, entities "
                    "decoded, spaces collapsed"
                )
            if spec["kind"] == "doc":
                sha = sha256_bytes(raw)
                entry["sha256_basis"] = "bytes of the downloaded .doc file"
            else:  # the page shell changes on every request; hash the document body itself
                sha = sha256_bytes(content.encode("utf-8"))
                entry["sha256_basis"] = "UTF-8 bytes of the documentContent HTML extracted from the vbpl.vn page"
            chunks = chunk_by_article(paras, spec["keep_articles"])
            arts = sorted({c["article"] for c in chunks})
            path = write_chunks(doc_id, spec, chunks, spec["url"], sha, meta["retrieved_at"])
            entry.update(
                {
                    "status": "INGESTED" if chunks else "BLOCKED",
                    "license": LICENSE_LEGAL,
                    "retrieved_at": meta["retrieved_at"],
                    "http": {k: meta.get(k) for k in ("content_type", "last_modified", "etag", "final_url")},
                    "source_metadata": {
                        k: v
                        for k, v in meta.items()
                        if k
                        not in ("url", "final_url", "status", "content_type", "last_modified", "etag", "retrieved_at")
                    },
                    "sha256_of_source": sha,
                    "chunks_file": path.relative_to(ROOT).as_posix(),
                    "chunks_sha256": sha256_bytes(path.read_bytes()),
                    "chunk_count": len(chunks),
                    "articles_kept": f"{arts[0]}-{arts[-1]}" if arts else None,
                    "articles_missing_in_range": [
                        n for n in range(spec["keep_articles"][0], spec["keep_articles"][1] + 1) if n not in arts
                    ],
                }
            )
        except Exception as exc:  # noqa: BLE001 - report the blocker, keep going
            entry.update({"status": "BLOCKED", "error": str(exc)})
            print(f"BLOCKED {doc_id}: {exc}", file=sys.stderr)
        manifest_docs.append(entry)
        print(f"{doc_id}: {entry.get('status')} {entry.get('chunk_count')} chunks")

    ip = verify_ip_law()
    manifest_docs.append(check_p02())
    for d in manifest_docs:
        d.setdefault("notes", [])
        if d["doc_id"] == "qd18_2021":
            d["notes"] += [
                "Host: Viet Nam Disaster Prevention portal (vupc.mae.gov.vn) of the Ministry of Agriculture and "
                "Environment. The .doc file's own properties name thuvienphapluat.vn / LawSoft as its author, so the "
                "government site serves a file prepared by that publisher; the wording is the decree's.",
                "Source typos are kept as they are (e.g. 'tình Quảng Bình', '39°c', 'xâm nhập mận').",
                "Body articles 1-63 are chunked; the annexes (Phụ lục I-XIII, mostly tables) are not.",
                "In-force status of QĐ 18/2021 was not re-checked in this run.",
            ]
        if d["doc_id"] == "nd112_2024":
            d["notes"] += [
                "Host: Cơ sở dữ liệu quốc gia về pháp luật (vbpl.vn, Ministry of Justice), item 169866; the page "
                "marks the decree as partially in force.",
                "These chunks are the ORIGINAL 2024 wording. The decree was later amended by Nghị định 151/2025/NĐ-CP "
                "(from 1 July 2025, two-level local government: 'cấp huyện' duties moved) and Nghị định "
                "226/2025/NĐ-CP (from 15 August 2025, Điều 10); a consolidated text exists (VBHN). Check the current "
                "wording before giving procedural advice.",
                "Articles 1-20 are chunked; the annex forms (Phụ lục) are not.",
            ]
    manifest = {
        "dataset_id": "evidence_documents",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "pipeline/fetch_documents.py",
        "copyright_basis": ip,
        "documents": manifest_docs,
        "chunk_schema": [
            "doc_id",
            "source_id",
            "location",
            "text",
            "url",
            "license",
            "retrieved_at",
            "sha256_of_source",
            "chunk_id",
            "heading",
            "chapter",
        ],
        "chunking": (
            "One chunk per khoản (numbered clause) of each Điều; text of an article before its first khoản, "
            "or of an article without khoản, is one chunk located at 'Điều N'. Points a), b) stay inside "
            "their khoản. Wording is unchanged; only tags are removed and spaces collapsed."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = OUT / "MANIFEST.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {mpath}")


if __name__ == "__main__":
    main()

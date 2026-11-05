#!/usr/bin/env python3
"""Build an optimized AdGuard-style blocklist from configured public sources."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import os
import re
import tempfile
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES_FILE = os.path.join(BASE_DIR, "sources.txt")
WHITELIST_FILE = os.path.join(BASE_DIR, "whitelist.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "blocklist_optimized.txt")
MAX_RESPONSE_BYTES = 25 * 1024 * 1024
LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def load_entries(filepath):
    """Return non-empty, non-comment lines in file order."""
    entries = []
    if not os.path.exists(filepath):
        return entries
    with open(filepath, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line and not line.startswith(("#", "!")):
                entries.append(line)
    return entries


def normalize_domain(value):
    """Return a normalized domain, or None when value is not a valid domain."""
    value = value.strip().lower().rstrip(".")
    if value.startswith("||"):
        value = value[2:]
    value = value.lstrip("*.")
    value = value.rstrip("^")
    if not value or len(value) > 253 or "." not in value:
        return None
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    try:
        ipaddress.ip_address(value)
        return None
    except ValueError:
        pass
    labels = value.split(".")
    if any(not LABEL_RE.fullmatch(label) for label in labels):
        return None
    return value


def fetch_url(url):
    """Download a source with a timeout and a maximum response size."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print(f"[AVISO] URL ignorado (apenas HTTP/HTTPS): {url}")
        return url, None
    try:
        request = Request(url, headers={"User-Agent": "BlocklistAuto/1.0"})
        with urlopen(request, timeout=20) as response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
        if len(content) > MAX_RESPONSE_BYTES:
            raise ValueError(f"resposta excede {MAX_RESPONSE_BYTES} bytes")
        return url, content.decode("utf-8", errors="replace")
    except (OSError, URLError, ValueError) as error:
        print(f"[AVISO] Erro ao descarregar {url}: {error}")
        return url, None


def parse_lines(content):
    """Parse hosts-file entries, plain domains, and basic Adblock domain rules."""
    domains = set()
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "!", "/", "@@", "[")):
            continue

        # Hosts format: 0.0.0.0 domain.example (or 127.0.0.1 ...).
        fields = line.split()
        try:
            ipaddress.ip_address(fields[0])
            candidates = fields[1:]
        except (ValueError, IndexError):
            # Accept basic Adblock rules and bare domains, not arbitrary filters.
            if line.startswith("||"):
                candidate = line[2:].split("^", 1)[0].split("$", 1)[0]
                candidates = [candidate] if "/" not in candidate else []
            else:
                candidates = [line] if len(fields) == 1 else []

        for candidate in candidates:
            domain = normalize_domain(candidate)
            if domain:
                domains.add(domain)
    return domains


def is_whitelisted(domain, whitelist):
    """Whitelist a domain and all of its subdomains."""
    return any(domain == allowed or domain.endswith("." + allowed) for allowed in whitelist)


def optimize_domains(domains, whitelist):
    filtered = {domain for domain in domains if not is_whitelisted(domain, whitelist)}
    optimized = set()
    for domain in sorted(filtered, key=lambda item: (item.count("."), item)):
        labels = domain.split(".")
        if not any(".".join(labels[index:]) in optimized for index in range(1, len(labels))):
            optimized.add(domain)
    return sorted(optimized)


def write_output(domains):
    """Atomically replace the generated list, avoiding partial output files."""
    fd, temporary_path = tempfile.mkstemp(prefix=".blocklist-", dir=BASE_DIR, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            output.write("! Title: Automated Optimized AdGuard Blocklist\n")
            output.write("! Description: Atualizada, deduplicada e filtrada pela whitelist.\n")
            for domain in domains:
                output.write(f"||{domain}^\n")
        os.replace(temporary_path, OUTPUT_FILE)
    except Exception:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise


def main():
    print("[INFO] A iniciar a atualização das blocklists...")
    sources = load_entries(SOURCES_FILE)
    whitelist = {domain for entry in load_entries(WHITELIST_FILE)
                 if (domain := normalize_domain(entry))}
    if not sources:
        raise SystemExit("[ERRO] Nenhuma fonte encontrada em sources.txt")

    fetched = {}
    with ThreadPoolExecutor(max_workers=min(5, len(sources))) as executor:
        futures = [executor.submit(fetch_url, url) for url in sources]
        for future in as_completed(futures):
            url, content = future.result()
            if content is not None:
                fetched[url] = content
    if not fetched:
        raise SystemExit("[ERRO] Não foi possível descarregar nenhuma fonte; ficheiro existente preservado.")

    all_domains = set()
    for content in fetched.values():
        all_domains.update(parse_lines(content))
    final_domains = optimize_domains(all_domains, whitelist)
    write_output(final_domains)

    print(f"[INFO] Fontes descarregadas: {len(fetched)}/{len(sources)}")
    print(f"[INFO] Domínios recolhidos: {len(all_domains)}")
    print(f"[INFO] Domínios na whitelist: {len(whitelist)}")
    print(f"[SUCESSO] Domínios finais: {len(final_domains)}")
    print(f"[SUCESSO] Ficheiro gerado: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

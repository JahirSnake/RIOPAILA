import requests
from bs4 import BeautifulSoup
import time

SITEMAP_URL = "https://www.riopaila-castilla.com/wp-sitemap.xml"

# ---------------------------
# 1. Obtener URLs del sitemap
# ---------------------------
def get_urls_from_sitemap(sitemap_url):
    urls = []

    response = requests.get(sitemap_url)
    soup = BeautifulSoup(response.text, "xml")

    # WordPress usa sub-sitemaps
    sitemap_tags = soup.find_all("sitemap")

    if sitemap_tags:
        # hay sub-sitemaps
        for sitemap in sitemap_tags:
            sub_url = sitemap.find("loc").text
            urls.extend(get_urls_from_sitemap(sub_url))
    else:
        # sitemap normal con URLs
        url_tags = soup.find_all("url")
        for url in url_tags:
            loc = url.find("loc").text
            urls.append(loc)

    return urls


# ---------------------------
# 2. Extraer texto limpio
# ---------------------------
def extract_text(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # eliminar scripts y estilos
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        text = soup.get_text(separator=" ")

        # limpieza básica
        text = " ".join(text.split())

        return text

    except Exception as e:
        print(f"Error en {url}: {e}")
        return ""


# ---------------------------
# 3. MAIN
# ---------------------------
if __name__ == "__main__":

    print("Leyendo sitemap...")
    urls = get_urls_from_sitemap(SITEMAP_URL)

    print(f"Total URLs encontradas: {len(urls)}")

    all_text = ""

    for i, url in enumerate(urls):
        print(f"[{i+1}/{len(urls)}] Extrayendo: {url}")

        text = extract_text(url)

        if len(text) > 200:  # evita páginas vacías
            all_text += f"\n\n--- {url} ---\n\n"
            all_text += text

        time.sleep(0.5)

    # guardar
    with open("RUTA DONDE SE VA A GUARDAR SCRAPPING.TXT", "w", encoding="utf-8") as f:
        f.write(all_text)

    print("Scraping completo")
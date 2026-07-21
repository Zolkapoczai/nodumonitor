import os
import glob
from bs4 import BeautifulSoup

def build_knowledge_base(config: dict) -> str:
    """
    Végigmegy a config-ban megadott forrásmappákon, kinyeri a tartalmat
    (HTML fájlok esetén megtisztítva a szöveget), és összefűzi egyetlen 
    nagy .md fájlba, amit az AI rendszerpromptokhoz lehet injektálni.
    Visszaadja a generált fájl útvonalát.
    """
    kb_config = config.get("knowledge_base", {})
    folders = kb_config.get("folders", [])
    output_path = kb_config.get("output_file", "storage/nodu_knowledge_base.md")
    
    # Abszolút elérési útvonallá alakítás a biztonság kedvéért
    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)
    
    compiled_content = [
        "# NODU KNOWLEDGE BASE",
        "Ezt a dokumentumot a rendszer automatikusan állította elő a technikai és üzleti mappákból.",
        "Minden részletes információt innen vegyél, ha a NODU Bridge funkcióiról, korlátairól, "
        "licenszeléséről, fejlesztési irányairól (roadmap) vagy esettanulmányairól kérdeznek.",
        "--------------------------------------------------\n"
    ]
    
    files_processed = 0
    total_bytes = 0
    
    for folder in folders:
        if not os.path.isdir(folder):
            print(f"[knowledge] A mappa nem található: {folder}")
            continue
            
        print(f"[knowledge] Mappa feldolgozása: {folder}")
        
        # Minden fájlt megnézünk a mappában (nem feltétlenül rekurzívan, ahogy a lista kéri)
        for filepath in glob.glob(os.path.join(folder, "*.*")):
            if not os.path.isfile(filepath):
                continue
                
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in [".txt", ".md", ".html", ".htm"]:
                continue
                
            filename = os.path.basename(filepath)
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(filepath, "r", encoding="windows-1250") as f:
                        content = f.read()
                except Exception as e:
                    print(f"[knowledge] Hiba a(z) {filename} olvasásakor: {e}")
                    continue
            
            # Ha HTML, akkor kivonjuk belőle a tiszta szöveget
            if ext in [".html", ".htm"]:
                soup = BeautifulSoup(content, "html.parser")
                # Szkriptek és stílusok eltávolítása
                for script in soup(["script", "style", "head", "nav", "footer"]):
                    script.extract()
                text = soup.get_text(separator="\n", strip=True)
            else:
                text = content
                
            if not text.strip():
                continue
                
            compiled_content.append(f"## FILE: {filename}")
            compiled_content.append(f"Source: {filepath}")
            compiled_content.append("```\n" + text.strip() + "\n```\n")
            compiled_content.append("--------------------------------------------------\n")
            
            files_processed += 1
            total_bytes += len(text)
            
    with open(abs_output, "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(compiled_content))
        
    print(f"[knowledge] Tudásbázis sikeresen frissítve. Fájlok: {files_processed}, Méret: {total_bytes / 1024:.1f} KB")
    return abs_output

if __name__ == "__main__":
    import yaml
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            c = yaml.safe_load(f)
        build_knowledge_base(c)
    except Exception as e:
        print(f"Hiba: {e}")

"""Before/after benchmark: v1 (OpenRokEN/main.py at 4e11a457) vs the current code.

    python -m bench.comparar_v1

Synthetic game screens with real Tesseract OCR; the Gemini call is faked,
so network time is not measured.
"""
import csv, json, random, statistics, subprocess, tempfile, textwrap, time, types
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageGrab

REPO = Path(__file__).resolve().parent.parent
S = Path(tempfile.mkdtemp(prefix="openrok-bench-"))
V1 = "4e11a457"


def git_show(caminho):
    return subprocess.run(["git", "show", f"{V1}:{caminho}"], cwd=REPO, capture_output=True, text=True, check=True).stdout
random.seed(42)

# ---------------------------------------------------------- synthetic screen
try:
    FONT = ImageFont.truetype("/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf", 26)
    FONT_OPT = ImageFont.truetype("/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf", 24)
except OSError:
    FONT, FONT_OPT = ImageFont.load_default(size=26), ImageFont.load_default(size=24)
AREAS = {"Pergunta": (640, 335, 850, 120), "A": (623, 470, 405, 83), "B": (1085, 470, 405, 83),
         "C": (623, 570, 405, 83), "D": (1085, 570, 405, 83)}

def tela(pergunta, opcoes):
    img = Image.new("RGB", (1920, 1080), (40, 30, 20))
    d = ImageDraw.Draw(img)
    def caixa(area, texto, font, largura):
        x, y, w, h = area
        d.rectangle((x, y, x + w, y + h), fill=(232, 218, 186))
        linhas = textwrap.wrap(texto, largura)
        lh = font.size + 6
        ty = y + (h - lh * len(linhas)) // 2
        for i, l in enumerate(linhas):
            tw = d.textlength(l, font=font)
            d.text((x + (w - tw) / 2, ty + i * lh), l, font=font, fill=(60, 40, 20))
    caixa(AREAS["Pergunta"], pergunta, FONT, 58)
    for k, o in zip("ABCD", opcoes):
        caixa(AREAS[k], o, FONT_OPT, 30)
    return img

TELA = {"img": None, "grabs": 0}
def fake_grab(bbox=None, **kw):
    TELA["grabs"] += 1
    return TELA["img"].crop(bbox)
ImageGrab.grab = fake_grab

# ---------------------------------------------------------- load both versions
from openrok import banco, ia, ocr, texto as modulo_texto  # noqa: E402

novo = types.SimpleNamespace(
    BancoPerguntas=banco.BancoPerguntas, MotorOCR=ocr.MotorOCR,
    extrair_letra=ia.extrair_letra, normalizar=modulo_texto.normalizar, fuzz=modulo_texto.fuzz)

src = git_show("OpenRokEN/main.py")
src = src.split("# PROGRAM INITIALIZATION")[0]
antigo = types.ModuleType("antigo")
exec(compile(src, "antigo_main.py", "exec"), antigo.__dict__)
Old = antigo.OpenOCR

def linhas(p):
    with open(p, encoding="utf-8", newline="") as f:
        return [(r[0], r[1]) for r in csv.reader(f)]

CSV_ANTIGO = S / "perguntas_respostas_en.csv"
CSV_ANTIGO.write_text(git_show("OpenRokEN/perguntas_respostas_en.csv"), encoding="utf-8")
base = linhas(CSV_ANTIGO)
validas = [(q, a) for q, a in base[1:] if len(q.strip()) >= 15 and a.strip() and q != "#VALUE!"]

# ---------------------------------------------------------- OCR-like noise
TROCAS = {"l": "1", "o": "0", "e": "c", "i": "l", "a": "o", "s": "5", "m": "rn", ",": ".", "'": "’", "?": "2"}
def ruido(q, taxa):
    out = []
    for c in q:
        r = random.random()
        if r < taxa / 2 and c.lower() in TROCAS:
            out.append(TROCAS[c.lower()])
        elif r < taxa * 0.7:
            continue  # dropped char
        else:
            out.append(c)
    t = "".join(out)
    t = "\n".join(textwrap.wrap(t, 58))  # OCR line breaks
    if random.random() < 0.3:
        t = random.choice(["| ", "_ ", "‘"]) + t
    return t

class Dummy: pass

def matcher_antigo(db):
    d = Dummy(); d.perguntas_respostas = db
    def f(t):
        q, a = Old.buscar_pergunta_resposta(d, t)
        return None if a == "Not found" else a
    return f

def matcher_novo(db_rows):
    p = S / "tmp_db.csv"
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["question", "response"]); w.writerows(db_rows)
    b = novo.BancoPerguntas(p)
    def f(t):
        r = b.buscar(t)
        return None if r is None else r[1]
    return f

def avaliar(nome, f, consultas):
    acertos = erros = vazios = 0; tempos = []
    for texto, esperado in consultas:
        t0 = time.perf_counter(); r = f(texto); tempos.append(time.perf_counter() - t0)
        if r is None: vazios += 1
        elif esperado is not None and r.strip() == esperado.strip(): acertos += 1
        else: erros += 1
    n = len(consultas)
    return {"versao": nome, "n": n, "acerto": acertos / n, "resposta_errada": erros / n, "nao_encontrou": vazios / n,
            "ms_mediana": statistics.median(tempos) * 1000, "ms_p95": sorted(tempos)[int(n * .95)] * 1000}

R = {}

# ---------------------------------------------------------- 1) matching on known questions
amostra = random.sample(validas, 400)
for taxa in (0.0, 0.03, 0.08):
    consultas = [(ruido(q, taxa), a) for q, a in amostra]
    R[f"conhecidas_ruido_{int(taxa*100)}%"] = [
        avaliar("antes", matcher_antigo(base), consultas),
        avaliar("depois", matcher_novo(base[1:]), consultas)]

# ---------------------------------------------------------- 2) unknown questions (should NOT match)
fora = random.sample(validas, 200)
fora_set = set(fora)
base_sem = [r for r in base if r not in fora_set]
consultas = [(ruido(q, 0.03), None) for q, _ in fora]
R["desconhecidas (falso positivo = resposta_errada)"] = [
    avaliar("antes", matcher_antigo(base_sem), consultas),
    avaliar("depois", matcher_novo(base_sem[1:]), consultas)]

# short OCR garbage (partial read)
lixo = [(q[:random.randint(6, 14)], None) for q, _ in random.sample(validas, 200)]
R["fragmentos curtos de OCR (falso positivo = resposta_errada)"] = [
    avaliar("antes", matcher_antigo(base), lixo),
    avaliar("depois", matcher_novo(base[1:]), lixo)]

# ---------------------------------------------------------- 3) full pipeline with real Tesseract OCR
import tesserocr
from openrok.caminhos import pasta_tessdata  # noqa: E402
TESS = pasta_tessdata()
_orig = tesserocr.PyTessBaseAPI
def API(*a, **k):
    k.setdefault("path", TESS); return _orig(*a, **k)
tesserocr.PyTessBaseAPI = API
antigo.tesserocr.PyTessBaseAPI = API

opcoes_pool = [a for _, a in validas]
casos = []
for q, a in random.sample(validas, 60):
    ops = random.sample(opcoes_pool, 3) + [a]; random.shuffle(ops)
    casos.append((q, a, ops))

def pipeline_antigo(caso, acerto_banco):
    """Same steps as OpenOCR.responde(), minus Tk and Gemini network."""
    TELA["img"] = tela(caso[0], caso[2])
    t0 = time.perf_counter()
    txt = Old.extrair_texto(None, Old.processar_imagem(None, AREAS["Pergunta"]))
    d = Dummy(); d.perguntas_respostas = base if acerto_banco else base_vazia
    q, r = Old.buscar_pergunta_resposta(d, txt)
    ops = None
    if r == "Not found":
        ops = [Old.extrair_texto(None, Old.processar_imagem(None, AREAS[k])) for k in "ABCD"]
        r = ops[caso[2].index(caso[1])]  # Gemini picks the right option, echoed as read by OCR
    return time.perf_counter() - t0, r, txt, ops

base_vazia = [base[0]]
(S / "tmp_vazio.csv").write_text("question,response\n", encoding="utf-8")

from openrok.banco import mapear_resposta  # noqa: E402
from openrok.geometria import Ret, areas_para  # noqa: E402

GEO = areas_para(Ret(0, 0, 1920, 1080))
ENV = GEO.envoltorio()

t0 = time.perf_counter()
motor = novo.MotorOCR("eng")
inicializacao_ocr = time.perf_counter() - t0
banco_cheio = novo.BancoPerguntas(CSV_ANTIGO)
banco_vazio = novo.BancoPerguntas(S / "tmp_vazio.csv")


def pipeline_novo(caso, acerto_banco):
    """The watcher's path: one capture, question + options read in parallel, lookup, answer -> letter."""
    TELA["img"] = tela(caso[0], caso[2])
    banco_atual = banco_cheio if acerto_banco else banco_vazio
    t0 = time.perf_counter()
    imagem = ImageGrab.grab(bbox=(ENV.x, ENV.y, ENV.x + ENV.w, ENV.y + ENV.h))
    texto, opcoes = motor.ler_tudo(GEO.pergunta.recortar(imagem, ENV),
                                   [GEO.texto_opcao(letra).recortar(imagem, ENV) for letra in "ABCD"])
    achada = banco_atual.buscar(texto)
    letra = mapear_resposta(achada[1], opcoes) if achada else None
    if letra is None:
        letra = "ABCD"[caso[2].index(caso[1])]  # simulated AI picks the right option, no network
    return time.perf_counter() - t0, opcoes["ABCD".index(letra)]

for rotulo, hit in (("pergunta_no_banco", True), ("pergunta_nova (OCR das 4 opcoes, Gemini simulado)", False)):
    res = {}
    for nome, fn in (("antes", pipeline_antigo), ("depois", pipeline_novo)):
        fn(casos[0], hit)  # warm-up
        TELA["grabs"] = 0
        tempos, certos = [], 0
        for c in casos:
            out = fn(c, hit)
            tempos.append(out[0]); certos += novo.fuzz.ratio(novo.normalizar(out[1] or ""), novo.normalizar(c[1])) >= 90
        res[nome] = {"ms_mediana": statistics.median(tempos) * 1000, "ms_p95": sorted(tempos)[int(len(tempos) * .95)] * 1000,
                     "acerto": certos / len(casos), "capturas_de_tela_por_busca": TELA["grabs"] / len(casos)}
    R["pipeline_" + rotulo] = res

# OCR quality of the options (miss path) - validated answers vs raw
R["inicializacao_motor_ocr_depois_s"] = inicializacao_ocr

# ---------------------------------------------------------- 4) Gemini reply handling
respostas_gemini = ["B", "B)", "b", "Answer: B", "The correct answer is B) Achilles", "**C**",
                    "Achilles", "A gladiator", "", None, "A or B", "I think it is D."]
OPS = ["A slave", "A gladiator", "Achilles", "A senator"]
R["tratamento_resposta_gemini"] = {
    repr(t): {"antes_salva_no_csv": repr(t), "depois_letra": novo.extrair_letra(t, OPS)} for t in respostas_gemini}

print(json.dumps(R, indent=1, ensure_ascii=False))

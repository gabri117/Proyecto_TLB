# tlb_interactivo.py
# Subtema: (6) TLB - Simulador interactivo por consola
# - TLB set-associative con LRU por conjunto
# - Generador de trazas con localidad
# - EMAT simple: Hit => t_tlb + t_mem ; Miss => t_tlb + t_pagewalk + t_mem
# - Menú interactivo para ajustar parámetros y comparar escenarios

from collections import deque
import random
import sys
import time

# ----------------------------- Núcleo TLB -----------------------------

class SetAssociativeTLB:
    def __init__(self, sets: int, ways: int):
        assert sets > 0 and ways > 0
        self.sets = sets
        self.ways = ways
        self.buckets = [deque() for _ in range(sets)]
        self.mask = sets - 1
        assert (sets & self.mask) == 0, "sets debe ser potencia de 2 (ej. 8,16,32,64,128)"

    def _index(self, vpn: int) -> int:
        return vpn & self.mask

    def access(self, vpn: int) -> bool:
        idx = self._index(vpn)
        bucket = self.buckets[idx]
        for tag in bucket:
            if tag == vpn:
                bucket.remove(tag)
                bucket.appendleft(tag)  # MRU
                return True
        if len(bucket) >= self.ways:
            bucket.pop()  # expulsa LRU
        bucket.appendleft(vpn)  # MRU
        return False

# ----------------------- Generador de trazas -------------------------

def generate_trace(
    n_accesses=20_000,
    vpages=8192,
    page_size=4096,
    locality_prob=0.85,
    locality_window=16,
    seed=42
):
    random.seed(seed)
    refs = []
    current = random.randrange(vpages)
    for _ in range(n_accesses):
        if random.random() < locality_prob:
            delta = random.randint(-locality_window // 2, locality_window // 2)
            vpn = (current + delta) % vpages
        else:
            vpn = random.randrange(vpages)
            current = vpn
        offset = random.randrange(page_size)
        refs.append((vpn, offset))
    return refs

# -------------------------- Simulación TLB ---------------------------

def run_tlb_sim(
    sets=64,
    ways=4,
    vpages=8192,
    page_size=4096,
    n_accesses=20_000,
    locality_prob=0.85,
    locality_window=16,
    t_tlb=1,
    t_mem=100,
    t_pagewalk=300,
    seed=42,
    show_progress=False
):
    tlb = SetAssociativeTLB(sets=sets, ways=ways)
    trace = generate_trace(
        n_accesses=n_accesses,
        vpages=vpages,
        page_size=page_size,
        locality_prob=locality_prob,
        locality_window=locality_window,
        seed=seed
    )

    hits = 0
    total_time = 0
    accesses = len(trace)
    step = max(1, accesses // 50)

    for i, (vpn, _) in enumerate(trace, start=1):
        hit = tlb.access(vpn)
        if hit:
            hits += 1
            total_time += (t_tlb + t_mem)
        else:
            total_time += (t_tlb + t_pagewalk + t_mem)

        if show_progress and (i % step == 0 or i == accesses):
            pct = int(i * 100 / accesses)
            bar_len = 40
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "·" * (bar_len - filled)
            print(f"\rProgreso: [{bar}] {pct:3d}%   ", end="", flush=True)

    if show_progress:
        print()  # salto de línea

    hit_rate = hits / accesses
    emat = total_time / accesses
    return {
        "accesses": accesses,
        "hits": hits,
        "misses": accesses - hits,
        "hit_rate": hit_rate,
        "EMAT": emat,
        "params": {
            "sets": sets, "ways": ways, "vpages": vpages, "page_size": page_size,
            "n_accesses": n_accesses, "locality_prob": locality_prob, "locality_window": locality_window,
            "t_tlb": t_tlb, "t_mem": t_mem, "t_pagewalk": t_pagewalk, "seed": seed
        }
    }

# --------------------------- Utilidades UI ---------------------------

def ask_int(prompt, default=None, minv=None, maxv=None):
    while True:
        try:
            raw = input(f"{prompt} [{default}]: ").strip()
            if raw == "" and default is not None:
                val = int(default)
            else:
                val = int(raw)
            if minv is not None and val < minv:
                print(f"  * Debe ser >= {minv}")
                continue
            if maxv is not None and val > maxv:
                print(f"  * Debe ser <= {maxv}")
                continue
            return val
        except ValueError:
            print("  * Ingresa un número entero válido.")

def ask_float(prompt, default=None, minv=None, maxv=None):
    while True:
        try:
            raw = input(f"{prompt} [{default}]: ").strip()
            if raw == "" and default is not None:
                val = float(default)
            else:
                val = float(raw)
            if minv is not None and val < minv:
                print(f"  * Debe ser >= {minv}")
                continue
            if maxv is not None and val > maxv:
                print(f"  * Debe ser <= {maxv}")
                continue
            return val
        except ValueError:
            print("  * Ingresa un número válido (puede ser decimal).")

def is_power_of_two(x: int) -> bool:
    return x > 0 and (x & (x - 1)) == 0

def print_result(title, result):
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)
    p = result["params"]
    print(f"TLB: sets={p['sets']}  ways={p['ways']}  entradas={p['sets']*p['ways']}")
    print(f"Traza: accesos={result['accesses']}, vpages={p['vpages']}, page_size={p['page_size']}")
    print(f"Localidad: prob={p['locality_prob']:.2f}, ventana={p['locality_window']}")
    print(f"Costos: t_tlb={p['t_tlb']}, t_mem={p['t_mem']}, t_pagewalk={p['t_pagewalk']}")
    print("-" * 64)
    print(f"{'Hits TLB':>16}: {result['hits']}")
    print(f"{'Misses TLB':>16}: {result['misses']}")
    print(f"{'Tasa de hit':>16}: {result['hit_rate']:.2%}")
    print(f"{'EMAT':>16}: {result['EMAT']:.2f} (unidades relativas)")
    # Mini-histograma ASCII de tasa de hit
    bars = int(result["hit_rate"] * 40)
    print(f"{'Hit bar':>16}: " + "█" * bars + "·" * (40 - bars))

def pause():
    input("\nPresiona ENTER para continuar...")

# ------------------------------ Menú --------------------------------

def main_menu():
    # Parámetros por defecto
    params = {
        "sets": 64,              # potencia de 2
        "ways": 4,               # asociatividad
        "vpages": 8192,
        "page_size": 4096,
        "n_accesses": 30_000,
        "locality_prob": 0.85,
        "locality_window": 16,
        "t_tlb": 1,
        "t_mem": 100,
        "t_pagewalk": 300,
        "seed": 123
    }

    while True:
        print("\n" + "="*64)
        print(" SIMULADOR INTERACTIVO: TLB (Subtema 6) ")
        print("="*64)
        print("1) Correr simulación con parámetros actuales")
        print("2) Ajustar parámetros del TLB")
        print("3) Ajustar traza (localidad y tamaño)")
        print("4) Ajustar costos (t_tlb, t_mem, t_pagewalk)")
        print("5) Comparar escenarios (tabla rápida)")
        print("6) Reset a valores por defecto")
        print("0) Salir")
        choice = input("\nElige una opción: ").strip()

        if choice == "1":
            show = input("¿Mostrar barra de progreso? (s/n) [n]: ").strip().lower() == "s"
            res = run_tlb_sim(
                sets=params["sets"], ways=params["ways"],
                vpages=params["vpages"], page_size=params["page_size"],
                n_accesses=params["n_accesses"],
                locality_prob=params["locality_prob"], locality_window=params["locality_window"],
                t_tlb=params["t_tlb"], t_mem=params["t_mem"], t_pagewalk=params["t_pagewalk"],
                seed=params["seed"],
                show_progress=show
            )
            print_result("RESULTADOS", res)
            pause()

        elif choice == "2":
            while True:
                s = ask_int("Número de sets (potencia de 2)", params["sets"], 1)
                if not is_power_of_two(s):
                    print("  * Debe ser potencia de 2 (ej. 8,16,32,64,128).")
                else:
                    params["sets"] = s
                    break
            params["ways"] = ask_int("Asociatividad (ways)", params["ways"], 1, 64)
            print("  ✓ Actualizado.")
            pause()

        elif choice == "3":
            params["vpages"] = ask_int("Páginas virtuales (vpages)", params["vpages"], 64)
            params["page_size"] = ask_int("Tamaño de página (bytes)", params["page_size"], 256)
            params["n_accesses"] = ask_int("Número de accesos en la traza", params["n_accesses"], 100)
            params["locality_prob"] = ask_float("Prob. de localidad [0-1]", params["locality_prob"], 0.0, 1.0)
            params["locality_window"] = ask_int("Ventana de localidad (páginas)", params["locality_window"], 1)
            params["seed"] = ask_int("Semilla aleatoria", params["seed"], 0)
            print("  ✓ Actualizado.")
            pause()

        elif choice == "4":
            params["t_tlb"] = ask_int("Costo t_tlb", params["t_tlb"], 0)
            params["t_mem"] = ask_int("Costo t_mem", params["t_mem"], 1)
            params["t_pagewalk"] = ask_int("Costo t_pagewalk", params["t_pagewalk"], 0)
            print("  ✓ Actualizado.")
            pause()

        elif choice == "5":
            # Compara variando ways y sets para mostrar impacto en TLB hit y EMAT
            print("\nComparando ways ∈ {1,2,4,8} con sets fijo =", params["sets"])
            headers = ["ways", "hit_rate", "EMAT"]
            print(f"{headers[0]:>6} | {headers[1]:>10} | {headers[2]:>10}")
            print("-"*33)
            for ways in [1, 2, 4, 8]:
                res = run_tlb_sim(
                    sets=params["sets"], ways=ways,
                    vpages=params["vpages"], page_size=params["page_size"],
                    n_accesses=params["n_accesses"],
                    locality_prob=params["locality_prob"], locality_window=params["locality_window"],
                    t_tlb=params["t_tlb"], t_mem=params["t_mem"], t_pagewalk=params["t_pagewalk"],
                    seed=params["seed"]
                )
                print(f"{ways:6d} | {res['hit_rate']*100:9.2f}% | {res['EMAT']:9.2f}")
            print("\nComparando sets ∈ {8,16,32,64,128} con ways fijo =", params["ways"])
            headers = ["sets", "hit_rate", "EMAT"]
            print(f"{headers[0]:>6} | {headers[1]:>10} | {headers[2]:>10}")
            print("-"*33)
            for sets in [8, 16, 32, 64, 128]:
                # salta si no es potencia de 2 válida
                if not is_power_of_two(sets):
                    continue
                res = run_tlb_sim(
                    sets=sets, ways=params["ways"],
                    vpages=params["vpages"], page_size=params["page_size"],
                    n_accesses=params["n_accesses"],
                    locality_prob=params["locality_prob"], locality_window=params["locality_window"],
                    t_tlb=params["t_tlb"], t_mem=params["t_mem"], t_pagewalk=params["t_pagewalk"],
                    seed=params["seed"]
                )
                print(f"{sets:6d} | {res['hit_rate']*100:9.2f}% | {res['EMAT']:9.2f}")
            pause()

        elif choice == "6":
            params = {
                "sets": 64, "ways": 4, "vpages": 8192, "page_size": 4096,
                "n_accesses": 30_000, "locality_prob": 0.85, "locality_window": 16,
                "t_tlb": 1, "t_mem": 100, "t_pagewalk": 300, "seed": 123
            }
            print("  ✓ Parámetros reiniciados.")
            pause()

        elif choice == "0":
            print("\n¡Listo! Gracias por usar el simulador TLB.")
            time.sleep(0.4)
            sys.exit(0)

        else:
            print("Opción no válida.")
            time.sleep(0.6)

if __name__ == "__main__":
    main_menu()

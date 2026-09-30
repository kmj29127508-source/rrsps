"""
greedy2.py — 우선순위를 자유 조합할 수 있게 확장한 그리디 + 정렬형

1순위(그리디의 핵심 점수 계산 방식)와 2·3순위(동점일 때 볼 기준)를 자유 조합할 수 있어요.
"""
import random

PRIMARY_LABELS = {
    "count": "지금 만들면 바로 끝나는 주문 수",
    "count_partial": "지금 만들면 바로 끝나는 주문 수 (거의 다 끝난 주문도 미리 반영)",
    "count_ddweighted": "지금 만들면 바로 끝나는 주문 수 (새벽배송 주문을 2배 중요하게)",
}
TIE_LABELS = {
    "none": "사용 안 함",
    "time_asc": "생산시간이 짧은 것",
    "demand_desc": "이 상품을 필요로 하는 대기 주문이 많은 것",
    "cells_asc": "선반 칸을 적게 차지하는 것",
    "qty_desc": "오늘 만들 개수가 많은 것",
}
SORT_LABELS = {
    "qty_desc": "오늘 만들 개수가 많은 순",
    "qty_asc": "오늘 만들 개수가 적은 순",
    "time_asc": "생산시간이 짧은 순",
    "demand_desc": "필요로 하는 주문이 많은 순",
    "cells_asc": "선반 칸을 적게 차지하는 순",
    "code": "상품코드 순 (특별한 기준 없음)",
    "random": "무작위",
}


def prep_day(P, day, sku):
    """하루치 데이터를 한 번만 정리해서, 여러 config에 재사용한다."""
    needs = day.groupby("ORDER_NO")["SKU_CD"].apply(set).to_dict()
    typ = day.groupby("ORDER_NO")["DELIVERY_TYPE"].first().to_dict()
    qty = day.groupby("SKU_CD")["QTY"].sum().to_dict()
    orders_of = {}
    for o, skus in needs.items():
        for x in skus:
            orders_of.setdefault(x, []).append(o)
    demand_total = {x: len(v) for x, v in orders_of.items()}
    dur = {x: sku.at[x, "SETUP_SEC"] + sku.at[x, "UNIT_SEC"] * qty[x] for x in qty}
    cells = {x: P._cells(qty[x], sku.at[x, "PER_CELL"], sku.at[x, "CELLS_PER_UNIT"]) for x in qty}
    return dict(needs=needs, typ=typ, qty=qty, orders_of=orders_of,
                demand_total=demand_total, dur=dur, cells=cells)


def greedy2(ctx, primary="count", ties=()):
    needs, typ, qty, orders_of = ctx["needs"], ctx["typ"], ctx["qty"], ctx["orders_of"]
    dur, cells = ctx["dur"], ctx["cells"]

    def one_tie(name, x, demand):
        if name == "time_asc": return -dur[x]
        if name == "demand_desc": return demand
        if name == "cells_asc": return -cells[x]
        if name == "qty_desc": return qty[x]
        return 0

    remaining = set(orders_of)
    pending = set(needs)
    made, seq = set(), []
    while remaining:
        best, best_key = None, None
        for x in sorted(remaining):
            score, demand = 0.0, 0
            for o in orders_of[x]:
                if o not in pending:
                    continue
                demand += 1
                left = needs[o] - made
                if len(left) == 1:
                    score += 2.0 if (primary == "count_ddweighted" and typ[o] == "DD") else 1.0
                elif primary == "count_partial":
                    score += 1.0 / len(left)
            key = (score,) + tuple(one_tie(t, x, demand) for t in ties)
            if best_key is None or key > best_key:
                best, best_key = x, key
        seq.append(best)
        made.add(best)
        remaining.remove(best)
        pending = {o for o in pending if not needs[o] <= made}
    return seq


def static_sort(ctx, key):
    qty, dur, cells, demand_total = ctx["qty"], ctx["dur"], ctx["cells"], ctx["demand_total"]
    skus = sorted(qty)
    if key == "code": return skus
    if key == "qty_desc": return sorted(skus, key=lambda x: (-qty[x], x))
    if key == "qty_asc": return sorted(skus, key=lambda x: (qty[x], x))
    if key == "time_asc": return sorted(skus, key=lambda x: (dur[x], x))
    if key == "demand_desc": return sorted(skus, key=lambda x: (-demand_total[x], x))
    if key == "cells_asc": return sorted(skus, key=lambda x: (cells[x], x))
    if key == "random":
        s = skus[:]; random.Random(0).shuffle(s); return s
    raise ValueError(key)


def all_configs():
    configs = []
    for key in SORT_LABELS:
        configs.append({"family": "sort", "key": key})
    tie_keys = [k for k in TIE_LABELS if k != "none"]
    for primary in PRIMARY_LABELS:
        configs.append({"family": "greedy", "primary": primary, "tie2": "none", "tie3": "none"})
        for t2 in tie_keys:
            configs.append({"family": "greedy", "primary": primary, "tie2": t2, "tie3": "none"})
            for t3 in tie_keys:
                if t3 == t2: continue
                configs.append({"family": "greedy", "primary": primary, "tie2": t2, "tie3": t3})
    return configs


def config_id(cfg):
    if cfg["family"] == "sort":
        return f"sort:{cfg['key']}"
    return f"greedy:{cfg['primary']}:{cfg['tie2']}:{cfg['tie3']}"


def build_sequence(ctx, cfg):
    if cfg["family"] == "sort":
        return static_sort(ctx, cfg["key"])
    ties = tuple(t for t in (cfg["tie2"], cfg["tie3"]) if t != "none")
    return greedy2(ctx, primary=cfg["primary"], ties=ties)


# ---------------------------------------------------------------- 자동 탐색 (유전 알고리즘)
def _order_crossover(a, b, rng):
    n = len(a)
    i, j = sorted(rng.sample(range(n), 2))
    mid = a[i:j]
    rest = [x for x in b if x not in set(mid)]
    return rest[:i] + mid + rest[i:]


def genetic_sequence(P, day, sku, ctx, key_fn, budget=200, pop_size=10, seed=0):
    """여러 순서를 섞고 가끔 바꿔가며(교차+돌연변이), key_fn(작을수록 좋음) 점수를 줄여가는 탐색.
    key_fn(summary) -> 비교용 튜플. 시작 집단은 그리디 몇 가지로 채운다."""
    rng = random.Random(seed)
    cache = {}

    def score(seq):
        k = tuple(seq)
        if k not in cache:
            res = P.simulate_day(day, list(seq), sku)
            cache[k] = key_fn(res["summary"])
        return cache[k]

    seeds = [
        greedy2(ctx, primary="count_partial"),
        greedy2(ctx, primary="count", ties=("demand_desc",)),
        static_sort(ctx, "qty_desc"),
        static_sort(ctx, "demand_desc"),
    ]
    base = sorted(ctx["qty"])
    pop = [list(s) for s in seeds][:pop_size]
    while len(pop) < pop_size:
        s = base[:]
        rng.shuffle(s)
        pop.append(s)
    scored = sorted(((score(s), s) for s in pop), key=lambda t: t[0])
    calls = pop_size

    while calls < budget:
        children = []
        for _ in range(pop_size):
            p1 = min(rng.sample(scored, 3), key=lambda t: t[0])[1]
            p2 = min(rng.sample(scored, 3), key=lambda t: t[0])[1]
            c = _order_crossover(p1, p2, rng)
            if rng.random() < 0.5:
                i, j = rng.sample(range(len(c)), 2)
                c.insert(j, c.pop(i))
            children.append(c)
            calls += 1
            if calls >= budget:
                break
        scored = sorted(scored + [(score(c), c) for c in children], key=lambda t: t[0])[:pop_size]
    return scored[0][1]

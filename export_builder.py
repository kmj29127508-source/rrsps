"""
export_builder.py — "규칙 조립기" 웹페이지용 results.csv 만들기

1순위/2순위/3순위 조합을 전부(58가지) 계산해서 하나의 CSV로 저장한다.
웹페이지는 이 CSV에서 사용자가 고른 조합에 해당하는 행을 찾아서 보여준다.

노트북 사용법
    import os, sys
    os.chdir(r"...\한달생산스케쥴평가코드"); sys.path.append(os.getcwd())
    import production_sim as P, greedy2 as G2, export_builder as EB

    sku, lines = P.load_data()
    EB.export(P, sku, lines, dates=["2026-07-06"])   # 먼저 하루로 확인 (10~30초)
    EB.export(P, sku, lines)                          # 전체 27일 x 시나리오 (5~10분)
"""
import time
import pandas as pd
import greedy2 as G2

SCENARIOS = {
    "피커 1명 · DD→PD (strict)": dict(N_PICKERS=1, PICK_RULE="strict", TYPE_ORDER=["DD", "PD"]),
    "피커 2명 · DD→PD (strict)": dict(N_PICKERS=2, PICK_RULE="strict", TYPE_ORDER=["DD", "PD"]),
}
ALLOWED = {"N_PICKERS", "PICK_RULE", "TYPE_ORDER", "PICK_SEC_PER_ITEM"}


def metrics(P, res):
    sm = dict(res["summary"])
    od, pr = res["orders"], res["production"]
    n = sm["주문 수"]
    sm["Obj3_완료시각합(h)"] = od["DONE"].sum() / P.H
    sm["50%처리가능순번"] = int(pr.loc[pr["CUM_READY"] >= 0.5 * n, "STEP"].iloc[0])
    if P.N_PICKERS == 1:
        work = od["N_ITEMS"].sum() * P.PICK_SEC_PER_ITEM
        sm["피커유휴(h)"] = (od["DONE"].max() - work) / P.H
    return sm


def export(P, sku, lines, scenarios=None, dates=None, out="results.csv", configs=None, genetic_budget=200):
    scenarios = scenarios or SCENARIOS
    configs = configs or G2.all_configs()
    all_dates = sorted(lines["ORDER_DATE"].unique())
    dates = [pd.Timestamp(d).normalize() for d in dates] if dates else all_dates

    rows = []
    t0 = time.time()
    for name, params in scenarios.items():
        bad = set(params) - ALLOWED
        if bad:
            raise ValueError(f"'{name}'에 지원하지 않는 파라미터: {bad}")
        saved = {k: getattr(P, k) for k in params}
        try:
            for k, v in params.items():
                setattr(P, k, v)
            print(f"\n=== 시나리오: {name} ===")
            for d in dates:
                day = lines[lines["ORDER_DATE"] == d]
                ctx = G2.prep_day(P, day, sku)
                for cfg in configs:
                    seq = G2.build_sequence(ctx, cfg)
                    res = P.simulate_day(day, seq, sku)
                    rows.append({"시나리오": name, "설정": G2.config_id(cfg),
                                "날짜": d.strftime("%Y-%m-%d"), **metrics(P, res)})
                # 자동 탐색(유전 알고리즘) — 판정 기준(최대칸→DD완료→전체완료)과 같은 점수를 직접 줄임
                key_fn = lambda sm: (sm["최대 사용 칸 수"], 0.0 if pd.isna(sm["DD 처리 완료(h)"]) else sm["DD 처리 완료(h)"], sm["전체 처리 완료(h)"])
                seq = G2.genetic_sequence(P, day, sku, ctx, key_fn, budget=genetic_budget)
                res = P.simulate_day(day, seq, sku)
                rows.append({"시나리오": name, "설정": "search:genetic",
                            "날짜": d.strftime("%Y-%m-%d"), **metrics(P, res)})
                print(f"{d:%m-%d}", end=" | ")
        finally:
            for k, v in saved.items():
                setattr(P, k, v)
        print()

    df = pd.DataFrame(rows)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {out}  ({len(df):,}행, 설정 {len(configs)}개, {time.time()-t0:.0f}초)")
    return df


def export_config_labels(out="configs.csv"):
    """설정 id -> 사람이 읽는 설명 (웹페이지가 드롭다운을 만들 때 씀)"""
    rows = []
    for cfg in G2.all_configs():
        cid = G2.config_id(cfg)
        if cfg["family"] == "sort":
            rows.append({"설정": cid, "방식": "정렬형", "1순위": G2.SORT_LABELS[cfg["key"]], "2순위": "", "3순위": ""})
        else:
            rows.append({"설정": cid, "방식": "그리디형",
                        "1순위": G2.PRIMARY_LABELS[cfg["primary"]],
                        "2순위": G2.TIE_LABELS[cfg["tie2"]], "3순위": G2.TIE_LABELS[cfg["tie3"]]})
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {out}")

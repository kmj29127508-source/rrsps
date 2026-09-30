# 생산순서 최적화 — 규칙 조립기 (발표용 웹페이지)

생산 순서를 정하는 규칙을 **직접 조립**하고, `production_sim.py`로 미리 계산해둔 결과에서
바로 찾아 비교하는 페이지예요. 서버가 필요 없어서 GitHub Pages에 그대로 올릴 수 있어요.

## 화면 구성

1. **데이터 넣기** — `results.csv`를 끌어놓으면 바로 교체돼요
2. **규칙 조립기** — 두 갈래 중 하나로 순서를 정하는 규칙을 직접 만들어요
   - **정렬형**: 기준 하나로 한 번에 순서를 정함 (예: 수량 많은 순)
   - **그리디형**: 매 순간 다시 계산 — **1순위**(무엇으로 SKU를 고를지) → **2순위**(동점이면 무엇을 볼지) → **3순위**(그래도 동점이면)를 드롭다운으로 직접 조합
   - 조합할 때마다 "지금 조립한 규칙: ..."에 **문장으로 뜻이 그대로 보여요** (코드 아님)
   - 이미 계산된 조합만 추가할 수 있어요. 없는 조합은 버튼이 비활성화되고 안내가 떠요
3. **비교할 목록** — 추가한 규칙들이 쌓여요. baseline과 "자동 탐색(유전 알고리즘)"은 기본으로 들어있어요
4. **파라미터** — 시나리오(피커 수 등), 선반 한도, 판정 기준 1·2·3순위
5. **날짜 선택** — 전체 / 월요일만 / 평일만 / 직접 선택
6. **발표 모드** — 설정 패널을 숨기고 글자를 키움 (Esc로 복귀)

## 한계 (꼭 알아두세요)

브라우저 안에서는 파이썬 시뮬레이션을 다시 돌릴 수 없어요. 그래서:

- **규칙 조립기에서 만들 수 있는 조합**(정렬 7가지 × 그리디 1·2·3순위 조합 + 자동 탐색)은
  전부 미리 `export_builder.py`가 계산해서 `results.csv`에 넣어둔 것 중에서 **찾아 보여주는 것**이에요.
  화면에서 새로 계산하는 게 아니에요.
- 그래서 **"피커 3명" 같은 새 파라미터**나, **선반 크기 자체를 바꾸는 것**은 화면에서 안 돼요.
  파이썬에서 시나리오를 추가해서 `results.csv`를 다시 만들어야 해요.
- 선반 한도, 판정 기준, 날짜·규칙 선택은 CSV 안 값으로 화면에서 바로 계산돼요.

## 1. 내 결과 만들기 (노트북)

`greedy2.py`, `export_builder.py`를 `production_sim.py`와 같은 폴더에 넣고:

```python
import os, sys
os.chdir(r"C:\Users\kmj29\Desktop\한달생산스케쥴평가코드"); sys.path.append(os.getcwd())
import production_sim as P, greedy2 as G2, export_builder as EB

sku, lines = P.load_data()
EB.export(P, sku, lines, dates=["2026-07-06"])   # 먼저 하루로 확인 (30초~1분)
EB.export(P, sku, lines)                          # 전체 27일 × 시나리오 (5~10분)
```

`results.csv`가 생기면, 이 페이지에 먼저 끌어놓아서 확인하세요.

## 2. GitHub에 올리기 (브라우저만)

1. github.com → `+` → **New repository** → 이름 입력, **Public** 선택 → Create
2. **uploading an existing file** → 이 폴더의 `index.html`, `app.js`, `style.css`, `README.md`, `data` 폴더를
   전부 끌어놓기 → **Commit changes**
   (폴더째 말고, 폴더 **안의 것들**을 선택해서 끌어놓으세요)
3. **Settings → Pages → Deploy from a branch → `main` / `(root)` → Save**
4. 1~2분 뒤 `https://내아이디.github.io/저장소이름/`에서 열려요

## 3. 내 결과로 교체하기

1번에서 만든 `results.csv`를 저장소의 `data` 폴더에 올리면(같은 이름이면 덮어쓰기)
샘플 배너가 사라지고 내 결과가 나와요.

## 주의

- GitHub Pages 주소는 누구나 볼 수 있어요. `results.csv`에는 날짜별 요약 숫자만 있지만,
  `simple_data.xlsx`, `sku_size.xlsx` 같은 원본 파일은 **절대 올리지 마세요.**
- 로컬에서 `index.html`을 더블클릭해 열면 `data/results.csv`를 자동으로 못 읽어요(브라우저 보안).
  그때는 샘플이 뜨니 위 상자에 `results.csv`를 끌어놓으세요.

## 파일 구성

```
index.html / app.js / style.css   화면 (규칙 조립기, 표, 그래프)
data/sample_results.csv, .js       샘플 (임시 크기표로 만든 값, 실제 결과 아님)
data/results.csv                   ← 내 결과를 여기에 (GitHub에 올릴 때)
```

## 관련 파이썬 파일

```
greedy2.py          1·2·3순위를 자유 조합할 수 있는 그리디 + 정렬형 + 자동 탐색(유전 알고리즘)
export_builder.py   모든 조합을 계산해서 results.csv로 저장
```

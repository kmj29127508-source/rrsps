/* ============================================================
   조립기 앱 (app.js)
   ------------------------------------------------------------
   results.csv 로부터 1순위/2순위/3순위 규칙 조합을 분석 및 비교
   ============================================================ */

const REQUIRED = ["설정", "날짜", "최대 사용 칸 수"];

const FIELD = {
  scenario: "시나리오", config: "설정", date: "날짜",
  maxcells: "최대 사용 칸 수", avgcells: "평균 사용 칸 수",
  dd: "DD 처리 완료(h)", pd: "PD 처리 완료(h)", all: "전체 처리 완료(h)",
  obj3: "Obj3_완료시각합(h)", r50: "50%처리가능순번", idle: "피커유휴(h)",
};

const SORT_LABELS = {
  "sort:dd_ready": "DD우선 → 완료시각",
  "sort:ready_only": "완료시각 순",
  "sort:items_asc": "품목수 적은순",
  "sort:items_desc": "품목수 많은순",
};

const PRIMARY_LABELS = {
  "batch:size": "배치(크기순)",
  "batch:skew": "배치(편중순)",
  "slot:due": "칸(긴급완료빠른순)",
  "slot:size": "칸(잔여건수적은순)",
  "slot:remain": "칸(잔여작업적은순)",
  "slot:cells": "칸(사용칸적은순)",
  "slot:skew": "칸(편중순)",
  "order:dd_first": "주문(DD우선)",
  "order:items_asc": "주문(품목수적은순)",
  "order:items_desc": "주문(품목수많은순)",
  "order:ready_asc": "주문(생산완료빠른순)",
};

const TIE_LABELS = {
  "due": "긴급완료빠른순",
  "size": "잔여건수적은순",
  "remain": "잔여작업적은순",
  "cells": "사용칸적은순",
  "skew": "편중순",
  "items_asc": "품목수적은순",
};

const S = {
  rows: [],
  scenarios: [],
  allConfigsInData: new Set(),
  allDates: [],
  selectedScenario: "",
  metric1: "maxOfMax",
  metric2: "avgDD",
  metric3: "avgAll",
};

/* ---------- 초기화 및 이벤트 등록 ---------- */
document.addEventListener("DOMContentLoaded", () => {
  initUI();
  fetchDefaultCSV();
});

function initUI() {
  const fileInput = document.getElementById("fileInput");
  if (fileInput) fileInput.addEventListener("change", handleFileUpload);

  const scenarioSelect = document.getElementById("scenarioSelect");
  if (scenarioSelect) scenarioSelect.addEventListener("change", (e) => {
    S.selectedScenario = e.target.value;
    renderAll();
  });

  const pSel = document.getElementById("primarySelect");
  const t2Sel = document.getElementById("tie2Select");
  const t3Sel = document.getElementById("tie3Select");

  [pSel, t2Sel, t3Sel].forEach((el) => {
    if (el) el.addEventListener("change", renderSelectedResult);
  });

  populateDropdowns();
}

function populateDropdowns() {
  const pSel = document.getElementById("primarySelect");
  const t2Sel = document.getElementById("tie2Select");
  const t3Sel = document.getElementById("tie3Select");

  if (!pSel || !t2Sel || !t3Sel) return;

  pSel.innerHTML = "";
  for (const [k, v] of Object.entries(PRIMARY_LABELS)) {
    pSel.innerHTML += `<option value="${k}">${v}</option>`;
  }

  const fillTie = (el) => {
    el.innerHTML = "";
    for (const [k, v] of Object.entries(TIE_LABELS)) {
      el.innerHTML += `<option value="${k}">${v}</option>`;
    }
  };

  fillTie(t2Sel);
  fillTie(t3Sel);
  if (t3Sel.options.length > 1) t3Sel.selectedIndex = 1;
}

/* ---------- CSV 로딩 ---------- */
function fetchDefaultCSV() {
  fetch("results.csv")
    .then((res) => {
      if (!res.ok) throw new Error("기본 CSV 없음");
      return res.arrayBuffer();
    })
    .then((buf) => parseAndLoad(buf, "results.csv (기본)"))
    .catch(() => {
      showStatus("results.csv 파일을 업로드해 주세요.", "info");
    });
}

function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (evt) => parseAndLoad(evt.target.result, file.name);
  reader.readAsArrayBuffer(file);
}

function parseAndLoad(buf, source) {
  const text = decodeBuffer(buf);
  const table = parseCSV(text);
  const res = normalizeRows(table);

  if (res.error) {
    showStatus(res.error, "error");
    return;
  }

  S.rows = res.rows;
  S.allConfigsInData = new Set(S.rows.map((r) => r.config));
  S.scenarios = [...new Set(S.rows.map((r) => r.scenario))];
  S.allDates = [...new Set(S.rows.map((r) => r.date))].sort();
  S.selectedScenario = S.scenarios[0] || "기본";

  updateScenarioSelect();
  showStatus(`${source} — ${S.rows.length.toLocaleString()}행 로드 완료`, "success");
  renderAll();
}

function decodeBuffer(buf) {
  let t = new TextDecoder("utf-8").decode(buf);
  if (!t.includes("설정") || t.includes("\uFFFD")) {
    try {
      const k = new TextDecoder("euc-kr").decode(buf);
      if (k.includes("설정")) t = k;
    } catch (e) {}
  }
  return t;
}

function parseCSV(text) {
  const lines = text.split(/\r?\n/);
  return lines.map((line) => line.split(",").map((cell) => cell.replace(/^"|"$/g, "").trim()));
}

function normalizeRows(table) {
  if (!table.length) return { rows: [], error: "빈 파일입니다." };
  const header = table[0].map((h) => h.trim());
  const missing = REQUIRED.filter((c) => !header.includes(c));
  if (missing.length) {
    return { rows: [], error: `필수 열이 없습니다: ${missing.join(", ")}` };
  }
  const col = {};
  for (const [k, name] of Object.entries(FIELD)) col[k] = header.indexOf(name);
  const rows = [];
  for (let i = 1; i < table.length; i++) {
    const r = table[i];
    const get = (k) => (col[k] >= 0 ? r[col[k]] : undefined);
    const config = String(get("config") ?? "").trim();
    const date = String(get("date") ?? "").trim().slice(0, 10);
    if (!config || !date) continue;
    rows.push({
      scenario: String(get("scenario") ?? "").trim() || "기본",
      config, date,
      maxcells: num(get("maxcells")), avgcells: num(get("avgcells")),
      dd: num(get("dd")), pd: num(get("pd")), all: num(get("all")),
      obj3: num(get("obj3")), r50: num(get("r50")), idle: num(get("idle")),
    });
  }
  return rows.length ? { rows } : { rows: [], error: "데이터 행이 없습니다." };
}

function num(v) {
  const n = parseFloat(v);
  return isNaN(n) ? 0 : n;
}

/* ---------- 렌더링 ---------- */
function updateScenarioSelect() {
  const sel = document.getElementById("scenarioSelect");
  if (!sel) return;
  sel.innerHTML = S.scenarios.map((sc) => `<option value="${sc}">${sc}</option>`).join("");
  sel.value = S.selectedScenario;
}

function renderAll() {
  renderSelectedResult();
  renderTopRankings();
}

function renderSelectedResult() {
  const pSel = document.getElementById("primarySelect");
  const t2Sel = document.getElementById("tie2Select");
  const t3Sel = document.getElementById("tie3Select");
  const display = document.getElementById("selectedResultDisplay");
  if (!pSel || !t2Sel || !t3Sel || !display) return;

  const targetConfig = `g:${pSel.value}|${t2Sel.value}|${t3Sel.value}`;
  const filtered = S.rows.filter(
    (r) => r.scenario === S.selectedScenario && r.config === targetConfig
  );

  if (!filtered.length) {
    display.innerHTML = `<p class="warn">해당 설정(${targetConfig})의 결과 데이터가 없습니다.</p>`;
    return;
  }

  const maxCells = Math.max(...filtered.map((r) => r.maxcells));
  const avgDD = (filtered.reduce((a, b) => a + b.dd, 0) / filtered.length).toFixed(2);
  const avgAll = (filtered.reduce((a, b) => a + b.all, 0) / filtered.length).toFixed(2);

  display.innerHTML = `
    <div class="result-card">
      <h4>선택된 조합 평가 (${filtered.length}일 평균)</h4>
      <ul>
        <li><strong>월 최대 사용 칸 수:</strong> ${maxCells} 칸</li>
        <li><strong>평균 DD 처리 완료시간:</strong> ${avgDD} 시간</li>
        <li><strong>평균 전체 처리 완료시간:</strong> ${avgAll} 시간</li>
      </ul>
    </div>
  `;
}

function renderTopRankings() {
  const rankContainer = document.getElementById("rankingContainer");
  if (!rankContainer) return;

  const scenarioRows = S.rows.filter((r) => r.scenario === S.selectedScenario);
  const grouped = {};

  scenarioRows.forEach((r) => {
    if (!grouped[r.config]) grouped[r.config] = [];
    grouped[r.config].push(r);
  });

  const summaries = Object.entries(grouped).map(([cfg, rows]) => {
    const maxCells = Math.max(...rows.map((r) => r.maxcells));
    const avgDD = rows.reduce((a, b) => a + b.dd, 0) / rows.length;
    const avgAll = rows.reduce((a, b) => a + b.all, 0) / rows.length;
    return { cfg, maxCells, avgDD, avgAll };
  });

  summaries.sort((a, b) => a.maxCells - b.maxCells || a.avgDD - b.avgDD || a.avgAll - b.avgAll);

  let html = `<table><thead><tr><th>순위</th><th>설정 ID</th><th>월최대칸</th><th>평균 DD 완료(h)</th><th>평균 전체 완료(h)</th></tr></thead><tbody>`;
  summaries.slice(0, 10).forEach((s, idx) => {
    html += `<tr><td>${idx + 1}</td><td>${s.cfg}</td><td>${s.maxCells}</td><td>${s.avgDD.toFixed(2)}</td><td>${s.avgAll.toFixed(2)}</td></tr>`;
  });
  html += `</tbody></table>`;

  rankContainer.innerHTML = html;
}

function showStatus(msg, type) {
  const el = document.getElementById("statusMsg");
  if (el) {
    el.textContent = msg;
    el.className = `status ${type}`;
  }
}

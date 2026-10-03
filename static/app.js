const $ = (id) => document.getElementById(id);
const inr = (n) => "₹" + Number(n).toLocaleString("en-IN", {minimumFractionDigits: 2, maximumFractionDigits: 2});

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, {
    headers: {"Content-Type": "application/json"}, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Invalid input");
  return data;
}

// ---- tabs ----
document.querySelectorAll("nav button").forEach((b) => b.onclick = () => {
  document.querySelectorAll("nav button").forEach((x) => x.classList.remove("active"));
  document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
  b.classList.add("active");
  $(b.dataset.tab).classList.add("active");
  if (b.dataset.tab === "entries") loadEntries();
  if (b.dataset.tab === "farmers") loadFarmers();
});

function breakdownHtml(r) {
  const adj = (label, v, cls) => v ? `<div class="row"><span>${label}</span><span class="${cls}">${cls === "neg" ? "−" : "+"}${inr(v)}</span></div>` : "";
  const g = r.quality_gain;
  return `
    <div class="big">${inr(r.total)} <small style="font-size:14px;font-weight:400">(${inr(r.rate_per_litre)}/litre)</small></div>
    <div class="row"><span>Fat value (${r.fat_kg} kg fat)</span><span>${inr(r.fat_amount)}</span></div>
    <div class="row"><span>SNF value (${r.snf_kg} kg SNF)</span><span>${inr(r.snf_amount)}</span></div>
    ${adj("Low-SNF penalty", r.snf_penalty, "neg")}
    ${adj("High-fat bonus", r.fat_bonus, "pos")}
    <div class="row"><span>Quantity-only price would be</span><span>${inr(r.quantity_only_total)}</span></div>
    <div class="row"><b>Quality ${g >= 0 ? "gain" : "loss"}</b><b class="${g >= 0 ? "pos" : "neg"}">${g >= 0 ? "+" : "−"}${inr(Math.abs(g))}</b></div>`;
}

// ---- calculator ----
async function runCalc() {
  const body = {litres: +$("c_litres").value, fat: +$("c_fat").value, snf: +$("c_snf").value};
  try { $("c_result").innerHTML = breakdownHtml(await api("/calculate", {method: "POST", body})); }
  catch (e) { $("c_result").innerHTML = `<span class="neg">${e.message}</span>`; return; }
  const samples = [[3.0, 7.8], [3.5, 8.2], [4.0, 8.5], [4.5, 8.7], [5.5, 9.0]];
  let html = "<tr><th>FAT % / SNF %</th><th>Total</th><th>Per litre</th><th>vs flat rate</th></tr>";
  for (const [f, s] of samples) {
    const r = await api("/calculate", {method: "POST", body: {litres: body.litres, fat: f, snf: s}});
    html += `<tr><td>${f} / ${s}</td><td>${inr(r.total)}</td><td>${inr(r.rate_per_litre)}</td>
      <td class="${r.quality_gain >= 0 ? "pos" : "neg"}">${r.quality_gain >= 0 ? "+" : "−"}${inr(Math.abs(r.quality_gain))}</td></tr>`;
  }
  $("c_compare").innerHTML = html;
}
["c_litres", "c_fat", "c_snf"].forEach((id) => $(id).oninput = runCalc);

// ---- farmers ----
let farmers = [];
async function loadFarmers() {
  farmers = await api("/farmers");
  $("f_table").innerHTML = "<tr><th>Name</th><th>Phone</th><th>Village</th><th></th></tr>" +
    farmers.map((f) => `<tr><td>${f.name}</td><td>${f.phone || ""}</td><td>${f.village || ""}</td>
    <td><button class="del" onclick="delFarmer(${f.id})">Delete</button></td></tr>`).join("");
  const opts = farmers.map((f) => `<option value="${f.id}">${f.name}</option>`).join("");
  $("e_farmer").innerHTML = opts; $("s_farmer").innerHTML = opts;
}
window.delFarmer = async (id) => {
  if (!confirm("Delete this farmer and all their entries?")) return;
  await api("/farmers/" + id, {method: "DELETE"}); loadFarmers();
};
$("f_form").onsubmit = async (e) => {
  e.preventDefault();
  await api("/farmers", {method: "POST", body: {name: $("f_name").value, phone: $("f_phone").value || null, village: $("f_village").value || null}});
  e.target.reset(); loadFarmers();
};

// ---- entries ----
async function previewEntry() {
  const l = +$("e_litres").value, f = +$("e_fat").value, s = +$("e_snf").value;
  if (!l || !f || !s) { $("e_preview").innerHTML = ""; return; }
  try { $("e_preview").innerHTML = breakdownHtml(await api("/calculate", {method: "POST", body: {litres: l, fat: f, snf: s}})); }
  catch (e) { $("e_preview").innerHTML = `<span class="neg">${e.message}</span>`; }
}
["e_litres", "e_fat", "e_snf"].forEach((id) => $(id).oninput = previewEntry);

$("e_form").onsubmit = async (e) => {
  e.preventDefault();
  const msg = $("e_msg");
  try {
    const r = await api("/entries", {method: "POST", body: {
      farmer_id: +$("e_farmer").value, entry_date: $("e_date").value, session: $("e_session").value,
      litres: +$("e_litres").value, fat: +$("e_fat").value, snf: +$("e_snf").value}});
    msg.className = "msg ok"; msg.textContent = "Saved. Payment: " + inr(r.total);
    ["e_litres", "e_fat", "e_snf"].forEach((id) => $(id).value = "");
    $("e_preview").innerHTML = ""; loadEntries();
  } catch (err) { msg.className = "msg err"; msg.textContent = err.message; }
};
async function loadEntries() {
  if (!farmers.length) await loadFarmers();
  const rows = await api("/entries");
  $("e_table").innerHTML = "<tr><th>Date</th><th>Session</th><th>Farmer</th><th>Litres</th><th>FAT</th><th>SNF</th><th>Amount</th><th></th></tr>" +
    rows.slice(0, 50).map((r) => `<tr><td>${r.entry_date}</td><td>${r.session}</td><td>${r.farmer_name}</td>
    <td>${r.litres}</td><td>${r.fat}</td><td>${r.snf}</td><td>${inr(r.total)}</td>
    <td><button class="del" onclick="delEntry(${r.id})">✕</button></td></tr>`).join("");
}
window.delEntry = async (id) => { await api("/entries/" + id, {method: "DELETE"}); loadEntries(); };

// ---- summary ----
async function loadSummary() {
  const fid = $("s_farmer").value, month = $("s_month").value;
  if (!fid || !month) return;
  const s = await api(`/summary?farmer_id=${fid}&month=${month}`);
  $("s_csv").href = `/api/export.csv?farmer_id=${fid}&month=${month}`;
  $("s_result").innerHTML = `
    <div class="big">${inr(s.total_amount)}</div>
    <div class="row"><span>Entries</span><span>${s.entries}</span></div>
    <div class="row"><span>Total litres</span><span>${s.total_litres}</span></div>
    <div class="row"><span>Weighted avg FAT / SNF</span><span>${s.avg_fat}% / ${s.avg_snf}%</span></div>
    <div class="row"><span>Average rate</span><span>${inr(s.avg_rate_per_litre)}/litre</span></div>
    <div class="row"><span>Quantity-only would be</span><span>${inr(s.quantity_only_amount)}</span></div>
    <div class="row"><b>Quality effect</b><b class="${s.quality_gain >= 0 ? "pos" : "neg"}">${s.quality_gain >= 0 ? "+" : "−"}${inr(Math.abs(s.quality_gain))}</b></div>`;
  $("s_table").innerHTML = "<tr><th>Date</th><th>Litres</th><th>Amount</th></tr>" +
    s.daily.map((d) => `<tr><td>${d.date}</td><td>${d.litres}</td><td>${inr(d.total)}</td></tr>`).join("");
}
$("s_load").onclick = loadSummary;

// ---- rate card ----
const RATE_FIELDS = [
  ["fat_rate", "Fat rate (₹/kg fat)"], ["snf_rate", "SNF rate (₹/kg SNF)"], ["density", "Milk density (kg/L)"],
  ["min_snf", "Minimum SNF %"], ["snf_penalty_per_point", "SNF penalty (₹/L per point)"],
  ["premium_fat", "Premium FAT % threshold"], ["fat_bonus_per_point", "Fat bonus (₹/L per point)"],
  ["flat_rate_per_litre", "Flat rate for comparison (₹/L)"]];

function showStatus(el, text, kind, timeoutMs = 1800) {
  el.className = `msg ${kind}`;
  el.textContent = text;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.textContent = "";
    el.className = "msg";
  }, timeoutMs);
}

async function loadRates() {
  const rc = await api("/rate-card");
  $("r_form").innerHTML = RATE_FIELDS.map(([k, l]) => `<label>${l}<input id="r_${k}" type="number" step="0.01" value="${rc[k]}"></label>`).join("") +
    `<button type="submit">Save rate card</button><span id="r_msg" class="msg"></span>`;
}
$("r_form").onsubmit = async (e) => {
  e.preventDefault();
  const body = {}; RATE_FIELDS.forEach(([k]) => body[k] = +$("r_" + k).value);
  try {
    await api("/rate-card", {method: "PUT", body});
    showStatus($("r_msg"), "Saved", "ok", 1500);
    runCalc();
  } catch (err) {
    showStatus($("r_msg"), err.message, "err", 2500);
  }
};

// ---- init ----
const today = new Date().toISOString().slice(0, 10);
$("e_date").value = today; $("s_month").value = today.slice(0, 7);
runCalc(); loadRates(); loadFarmers();

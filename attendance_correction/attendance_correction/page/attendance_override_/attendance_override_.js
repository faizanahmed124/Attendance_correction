frappe.pages["attendance_override_"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Attendance Override Audit",
		single_column: true,
	});

	if (!document.getElementById("aa-styles")) {
		const style = document.createElement("style");
		style.id = "aa-styles";
		style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

      /* ── LIGHT THEME VARIABLES ── */
      .aa-wrap{
        --bg:#f4f6f9;
        --surface:#ffffff;
        --sur2:#f0f2f7;
        --border:#dde1eb;
        --accent:#d97706;
        --red:#dc2626;
        --green:#16a34a;
        --blue:#2563eb;
        --text:#1e2533;
        --muted:#64748b;
        --r:10px;
        background:var(--bg);
        color:var(--text);
        font-family:'DM Sans',sans-serif;
        font-size:14px;
        padding:24px;
        min-height:80vh;
        border-radius:10px;
      }

      .aa-filters{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:18px 20px;display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
      .aa-fg{display:flex;flex-direction:column;gap:5px;min-width:145px;}
      .aa-fg label{font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);}
      .aa-fg input,.aa-fg select{background:var(--sur2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:7px 10px;font-family:'DM Sans',sans-serif;font-size:13px;outline:none;transition:border-color .2s;}
      .aa-fg input:focus,.aa-fg select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(217,119,6,.12);}
      .aa-fg select option{background:#ffffff;}
      .aa-btn{padding:8px 18px;border-radius:6px;border:none;cursor:pointer;font-family:'Syne',sans-serif;font-size:13px;font-weight:700;transition:all .15s;display:inline-flex;align-items:center;gap:6px;}
      .aa-btn-p{background:var(--accent);color:#ffffff;box-shadow:0 2px 6px rgba(217,119,6,.3);}.aa-btn-p:hover{background:#b45309;}
      .aa-btn-g{background:var(--sur2);color:var(--muted);border:1px solid var(--border);}.aa-btn-g:hover{color:var(--text);border-color:#aab4c8;}

      .aa-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px;}
      .aa-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:18px 20px;position:relative;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);}
      .aa-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;}
      .aa-card.cy::before{background:var(--accent);}
      .aa-card.cr::before{background:var(--red);}
      .aa-card.cb::before{background:var(--blue);}
      .aa-card.cg::before{background:var(--green);}
      .aa-clbl{font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:8px;}
      .aa-cval{font-family:'Syne',sans-serif;font-size:28px;font-weight:800;line-height:1;}
      .aa-cval.y{color:var(--accent);}
      .aa-cval.r{color:var(--red);}
      .aa-cval.b{color:var(--blue);}
      .aa-cval.g{color:var(--green);font-size:15px;padding-top:7px;}
      .aa-csub{font-size:11px;color:var(--muted);margin-top:5px;}

      .aa-tbl-wrap{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);}
      .aa-tbl-hdr{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);flex-wrap:wrap;gap:10px;background:var(--surface);}
      .aa-tbl-title{font-family:'Syne',sans-serif;font-weight:700;font-size:14px;color:var(--text);}
      .aa-rowcount{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);background:var(--sur2);padding:3px 10px;border-radius:20px;border:1px solid var(--border);}
      .aa-srch{background:var(--sur2);border:1px solid var(--border);border-radius:6px;padding:6px 11px;color:var(--text);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;width:195px;transition:border-color .2s;}
      .aa-srch:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(217,119,6,.12);}
      .aa-expbtn{background:var(--sur2);border:1px solid var(--border);color:var(--muted);border-radius:6px;padding:6px 12px;font-size:11px;font-family:'DM Mono',monospace;cursor:pointer;transition:all .15s;}
      .aa-expbtn:hover{color:var(--text);border-color:var(--accent);}

      .aa-tbl-wrap table{width:100%;border-collapse:collapse;}
      .aa-tbl-wrap thead th{background:var(--sur2);text-align:left;padding:9px 13px;font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap;}
      .aa-tbl-wrap tbody tr{border-bottom:1px solid var(--border);transition:background .1s;}
      .aa-tbl-wrap tbody tr:last-child{border-bottom:none;}
      .aa-tbl-wrap tbody tr:hover{background:#fafbfd;}
      .aa-tbl-wrap tbody td{padding:9px 13px;vertical-align:middle;}

      .aa-ename{font-weight:500;color:var(--text);}
      .aa-eid{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);}
      .aa-mono{font-family:'DM Mono',monospace;font-size:12px;white-space:nowrap;color:var(--text);}
      .aa-chip{display:inline-block;padding:2px 8px;border-radius:4px;font-family:'DM Mono',monospace;font-size:11px;background:var(--sur2);border:1px solid var(--border);color:var(--text);}
      .aa-chg{display:flex;align-items:center;gap:7px;font-family:'DM Mono',monospace;font-size:12px;white-space:nowrap;}
      .aa-from{color:var(--muted);}
      .aa-arrow{color:#c4cad8;}
      .aa-tr{color:var(--red);font-weight:600;}
      .aa-tg{color:var(--green);font-weight:600;}
      .aa-tb{color:var(--blue);font-weight:600;}

      .aa-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap;}
      .aa-badge.br{background:rgba(220,38,38,.08);color:var(--red);border:1px solid rgba(220,38,38,.2);}
      .aa-badge.bg{background:rgba(22,163,74,.08);color:var(--green);border:1px solid rgba(22,163,74,.2);}
      .aa-badge.bb{background:rgba(37,99,235,.08);color:var(--blue);border:1px solid rgba(37,99,235,.2);}
      .aa-dot{width:6px;height:6px;border-radius:50%;display:inline-block;flex-shrink:0;}
      .aa-dot.r{background:var(--red);}
      .aa-dot.g{background:var(--green);}
      .aa-dot.b{background:var(--blue);}

      .aa-link{font-family:'DM Mono',monospace;font-size:11px;color:var(--accent);text-decoration:none;}
      .aa-link:hover{text-decoration:underline;}

      /* Username chip — amber tint on white */
      .aa-user-chip{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-family:'DM Mono',monospace;font-size:11px;font-weight:600;background:rgba(217,119,6,.09);color:var(--accent);border:1px solid rgba(217,119,6,.22);}

      .aa-state{text-align:center;padding:55px 20px;color:var(--muted);}
      .aa-sico{font-size:34px;margin-bottom:10px;}
      .aa-stitle{font-family:'Syne',sans-serif;font-size:15px;color:var(--text);margin-bottom:5px;}
      .aa-ssub{font-size:12px;}
      .aa-spin{width:22px;height:22px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:aa-spin .7s linear infinite;margin:0 auto 10px;}
      @keyframes aa-spin{to{transform:rotate(360deg);}}
    `;
		document.head.appendChild(style);
	}

	// Mount into page.main
	const $wrap = $('<div class="aa-wrap"></div>').appendTo(page.main);

	$wrap.html(`
    <div class="aa-filters">
      <div class="aa-fg"><label>From Date</label><input type="date" id="aa-from"/></div>
      <div class="aa-fg"><label>To Date</label><input type="date" id="aa-to"/></div>
      <div class="aa-fg"><label>Employee</label><input type="text" id="aa-emp" placeholder="Employee ID…"/></div>
      <div class="aa-fg"><label>Department</label><input type="text" id="aa-dept" placeholder="All departments…"/></div>
      <div class="aa-fg">
        <label>Override Type</label>
        <select id="aa-type">
          <option value="all">All Overrides</option>
          <option value="reduction">Manual Reductions Only</option>
          <option value="increase">Manual Increases Only</option>
        </select>
      </div>
      <div style="display:flex;gap:10px;align-items:center;">
        <button class="aa-btn aa-btn-p" id="aa-run">▶ Run Report</button>
        <button class="aa-btn aa-btn-g" id="aa-reset">Reset</button>
      </div>
    </div>
    <div class="aa-cards">
      <div class="aa-card cy"><div class="aa-clbl">Total Corrections</div><div class="aa-cval y" id="s-total">—</div><div class="aa-csub">Records modified</div></div>
      <div class="aa-card cr"><div class="aa-clbl">Manual Reductions</div><div class="aa-cval r" id="s-red">—</div><div class="aa-csub">Hours reduced manually</div></div>
      <div class="aa-card cb"><div class="aa-clbl">Employees Affected</div><div class="aa-cval b" id="s-emp">—</div><div class="aa-csub">Unique employees</div></div>
      <div class="aa-card cg"><div class="aa-clbl">Most Overridden Field</div><div class="aa-cval g" id="s-field">—</div><div class="aa-csub">Highest change frequency</div></div>
    </div>
    <div class="aa-tbl-wrap">
      <div class="aa-tbl-hdr">
        <div style="display:flex;align-items:center;gap:10px;">
          <span class="aa-tbl-title">Correction Log</span>
          <span class="aa-rowcount" id="aa-count">0 rows</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <input class="aa-srch" type="text" id="aa-srch" placeholder="🔍  Search…"/>
          <button class="aa-expbtn" id="aa-exp">⬇ Export CSV</button>
        </div>
      </div>
      <div id="aa-body">
        <div class="aa-state">
          <div class="aa-sico">📋</div>
          <div class="aa-stitle">No data loaded</div>
          <div class="aa-ssub">Apply filters and click Run Report.</div>
        </div>
      </div>
    </div>
  `);

	const now = new Date();
	const y = now.getFullYear(), m = String(now.getMonth()+1).padStart(2,"0"), d = String(now.getDate()).padStart(2,"0");
	$wrap.find("#aa-from").val(`${y}-${m}-01`);
	$wrap.find("#aa-to").val(`${y}-${m}-${d}`);

	let allRows = [];

	$wrap.find("#aa-run").on("click", loadReport);
	$wrap.find("#aa-reset").on("click", () => { $wrap.find("#aa-emp,#aa-dept").val(""); $wrap.find("#aa-type").val("all"); });
	$wrap.find("#aa-srch").on("input", function(){ filterTable(this.value); });
	$wrap.find("#aa-exp").on("click", exportCSV);

	function loadReport() {
		const args = {
			from_date:     $wrap.find("#aa-from").val(),
			to_date:       $wrap.find("#aa-to").val(),
			employee:      $wrap.find("#aa-emp").val(),
			department:    $wrap.find("#aa-dept").val(),
			override_type: $wrap.find("#aa-type").val(),
		};
		setLoading();
		frappe.call({
			method: "attendance_correction.attendance_correction.api.attendance_correction_audit.get_correction_audit",
			args: args,
			callback: function(r) {
				allRows = r.message || [];
				renderSummary(allRows);
				renderTable(allRows);
			},
			error: function(err) {
				console.error(err);
				showError("API call failed — check browser console.");
			},
		});
	}

	function renderSummary(rows) {
		const reds = rows.filter(r => r.is_reduction);
		const fc = {};
		reds.forEach(r => { fc[r.field_name] = (fc[r.field_name]||0)+1; });
		const top = Object.keys(fc).sort((a,b)=>fc[b]-fc[a])[0] || "—";
		$wrap.find("#s-total").text(rows.length);
		$wrap.find("#s-red").text(reds.length);
		$wrap.find("#s-emp").text(new Set(rows.map(r=>r.employee)).size);
		$wrap.find("#s-field").text(top);
	}

	function getUsername(r) {
		// first_name resolved from owner fallback in backend
		return r.first_name || r.username || r.changed_by || "—";
	}

	function getChangedBy(r) {
		// Show Frappe username or raw email/id
		return r.username || r.changed_by || "—";
	}

	function renderTable(rows) {
		$wrap.find("#aa-count").text(`${rows.length} row${rows.length!==1?"s":""}`);
		if (!rows.length) {
			$wrap.find("#aa-body").html(`<div class="aa-state"><div class="aa-sico">✅</div><div class="aa-stitle">No overrides found</div><div class="aa-ssub">No corrections match the selected filters.</div></div>`);
			return;
		}
		const tbody = rows.map(r => {
			const tc = r.is_reduction ? "aa-tr" : r.override_type==="Manual Increase" ? "aa-tg" : "aa-tb";
			const bc = r.is_reduction ? "br"    : r.override_type==="Manual Increase" ? "bg"    : "bb";
			const dc = r.is_reduction ? "r"     : r.override_type==="Manual Increase" ? "g"     : "b";
			const firstName  = getUsername(r);
			const changedBy  = getChangedBy(r);
			return `<tr>
        <td><div class="aa-ename">${esc(r.employee_name)}</div><div class="aa-eid">${esc(r.employee)}</div></td>
        <td class="aa-mono">${esc(r.attendance_date)}</td>
        <td style="font-size:12px;color:var(--muted);">${esc(r.department)}</td>
        <td><span class="aa-chip">${esc(r.field_name)}</span></td>
        <td><div class="aa-chg"><span class="aa-from">${esc(r.from_value)}</span><span class="aa-arrow">→</span><span class="${tc}">${esc(r.to_value)}</span></div></td>
        <td><span class="aa-badge ${bc}"><span class="aa-dot ${dc}"></span>${esc(r.override_type)}</span></td>
        <td><div style="font-size:12px;">${esc(changedBy)}</div><div class="aa-mono" style="font-size:11px;color:var(--muted);">${esc(r.changed_on)}</div></td>
        <td><span class="aa-user-chip">👤 ${esc(firstName)}</span></td>
        <td><a class="aa-link" href="/app/attendance/${esc(r.attendance_name)}" target="_blank">${esc(r.attendance_name)} ↗</a></td>
      </tr>`;
		}).join("");
		$wrap.find("#aa-body").html(`<table><thead><tr><th>Employee</th><th>Date</th><th>Department</th><th>Field</th><th>Change (From → To)</th><th>Override Type</th><th>Changed By</th><th>Username</th><th>Record</th></tr></thead><tbody>${tbody}</tbody></table>`);
	}

	function filterTable(q) {
		q = q.toLowerCase().trim();
		if (!q) { renderTable(allRows); return; }
		renderTable(allRows.filter(r => [r.employee,r.employee_name,r.department,r.field_name,r.changed_by,r.override_type,getUsername(r)].join(" ").toLowerCase().includes(q)));
	}

	function exportCSV() {
		if (!allRows.length) return;
		const hdrs = ["Employee","Employee Name","Department","Date","Field","From","To","Override Type","Changed By","Username","Changed On","Record"];
		const lines = [hdrs.join(",")];
		allRows.forEach(r => {
			lines.push([r.employee,r.employee_name,r.department,r.attendance_date,r.field_name,r.from_value,r.to_value,r.override_type,r.changed_by,getUsername(r),r.changed_on,r.attendance_name].map(v=>`"${String(v??"").replace(/"/g,'""')}"`).join(","));
		});
		const blob = new Blob([lines.join("\n")],{type:"text/csv"});
		const a = document.createElement("a");
		a.href = URL.createObjectURL(blob);
		a.download = `override_audit_${frappe.datetime.get_today()}.csv`;
		a.click();
	}

	function setLoading() {
		$wrap.find("#aa-body").html(`<div class="aa-state"><div class="aa-spin"></div><div class="aa-stitle">Loading audit data…</div></div>`);
		["#s-total","#s-red","#s-emp","#s-field"].forEach(id => $wrap.find(id).text("…"));
	}

	function showError(msg) {
		$wrap.find("#aa-body").html(`<div class="aa-state"><div class="aa-sico">⚠️</div><div class="aa-stitle">Something went wrong</div><div class="aa-ssub">${msg}</div></div>`);
	}

	function esc(str) {
		return String(str??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
	}
};
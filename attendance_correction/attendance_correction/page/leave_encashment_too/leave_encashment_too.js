const API = "attendance_correction.attendance_correction.page.leave_encashment_too.leave_encashment_too";

frappe.pages['leave-encashment-too'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Leave Encashment Tool',
		single_column: true
	});

	let employees = [];
	const selected = new Set();
	const $body = $('<div class="mt-3"></div>').appendTo(page.main);

	const fmt = (v) => format_currency(v || 0);

	const filters = {};
	const add_filter = (df) => {
		const field = page.add_field(Object.assign({ change: () => { filters[df.fieldname] = field.get_value(); render(); } }, df));
		return field;
	};
	add_filter({ fieldname: 'employee', label: __('Employee ID'), fieldtype: 'Data' });
	add_filter({ fieldname: 'employee_name', label: __('Employee Name'), fieldtype: 'Data' });
	add_filter({ fieldname: 'department', label: __('Department'), fieldtype: 'Link', options: 'Department' });

	$(`<style>
		.le-wrap { border: 1px solid var(--border-color); border-radius: var(--border-radius-md, 8px); overflow: auto; background: var(--card-bg, #fff); }
		.le-table { width: 100%; border-collapse: collapse; font-size: var(--text-md, 13px); }
		.le-table th, .le-table td { padding: 10px 16px; border-bottom: 1px solid var(--border-color); border-right: 1px solid var(--border-color); white-space: nowrap; vertical-align: middle; }
		.le-table th:last-child, .le-table td:last-child { border-right: 0; }
		.le-table tbody tr:last-child td { border-bottom: 0; }
		.le-table thead th { background: var(--subtle-fg, #f8f8f8); font-weight: 600; position: sticky; top: 0; }
		.le-table tbody tr:hover { background: var(--subtle-fg, #f8f8f8); }
		.le-table th, .le-table td { text-align: center; }
		.le-loader { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: 60px 0; color: var(--text-muted); }
		.le-spinner { width: 36px; height: 36px; border: 3px solid var(--border-color); border-top-color: var(--primary, #7c5cfc); border-radius: 50%; animation: le-spin .8s linear infinite; }
		@keyframes le-spin { to { transform: rotate(360deg); } }
	</style>`).appendTo(page.main);

	const matches = (e) => {
		const has = (v, q) => !q || (v || '').toLowerCase().includes(q.toLowerCase());
		return has(e.employee, filters.employee) && has(e.employee_name, filters.employee_name)
			&& (!filters.department || e.department === filters.department);
	};

	function show_loader(msg) {
		$body.html(`<div class="le-loader"><div class="le-spinner"></div><div>${frappe.utils.escape_html(msg)}</div></div>`);
	}

	function render() {
		if (!employees.length) {
			$body.html('<div class="text-muted p-4 text-center">No employees found in Leave Allocation.</div>');
			return;
		}
		const visible = employees.filter(matches);
		if (!visible.length) {
			$body.html('<div class="text-muted p-4 text-center">No employees match the filters.</div>');
			return;
		}
		const esc = frappe.utils.escape_html;
		const rows = visible.map((e) => `
			<tr>
				<td><input type="checkbox" class="le-sel" data-emp="${esc(e.employee)}" ${selected.has(e.employee) ? 'checked' : ''}></td>
				<td>${esc(e.employee)}</td>
				<td>${esc(e.employee_name || '')}</td>
				<td>${esc(e.department || '')}</td>
				<td>${flt(e.total_leaves)}</td>
				<td>${e.calculated || e.saved ? flt(e.days) : '-'}</td>
				<td>${e.calculated || e.saved ? fmt(e.total) : '-'}</td>
				<td>${e.saved ? '<span class="indicator-pill green">Saved</span>' : '<span class="indicator-pill orange">Not saved</span>'}</td>
			</tr>`).join('');
		$body.html(`
			<div class="le-wrap"><table class="le-table">
				<thead><tr>
					<th><input type="checkbox" class="le-sel-all" ${visible.every((e) => selected.has(e.employee)) ? 'checked' : ''}></th>
					<th>Employee ID</th><th>Employee Name</th><th>Department</th>
					<th>Total Leaves</th>
					<th>Remaining Encashment Days</th>
					<th>Total</th><th>Status</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table></div>`);
		$body.find('.le-sel').on('change', function () {
			const emp = $(this).data('emp');
			this.checked ? selected.add(emp) : selected.delete(emp);
			$body.find('.le-sel-all').prop('checked', visible.every((e) => selected.has(e.employee)));
		});
		$body.find('.le-sel-all').on('change', function () {
			visible.forEach((e) => (this.checked ? selected.add(e.employee) : selected.delete(e.employee)));
			$body.find('.le-sel').prop('checked', this.checked);
		});
	}

	// selected employees, or everyone when nothing is selected
	const targets = (only_calculated) => employees
		.filter((e) => (!selected.size || selected.has(e.employee)) && (!only_calculated || e.calculated))
		.map((e) => e.employee);

	// keep already-calculated values when the list is refreshed
	// pass a list of employees to refresh only those rows instead of the whole list
	function fetch_employees(only) {
		const subset = Array.isArray(only) && only.length ? only : null;
		if (!subset) show_loader(__('Getting employees...'));
		return frappe.call({ method: `${API}.get_employees`, args: subset ? { employees: subset } : {} }).then((r) => {
			const old = Object.fromEntries(employees.map((e) => [e.employee, e]));
			const fresh = (r.message || []).map((e) => Object.assign(e, old[e.employee] && old[e.employee].calculated
				? { days: old[e.employee].days, total: old[e.employee].total, calculated: 1, saved: e.saved && old[e.employee].saved }
				: {}));
			if (subset) {
				const by = Object.fromEntries(fresh.map((e) => [e.employee, e]));
				employees = employees.map((e) => by[e.employee] || e);
			} else {
				employees = fresh;
			}
			render();
		});
	}

	page.set_primary_action(__('Save'), () => {
		const emps = targets(true);
		if (!emps.length) {
			frappe.msgprint(__('Please calculate first.'));
			return;
		}
		frappe.call({
			method: `${API}.save_encashments`,
			args: { employees: emps },
			freeze: true,
			freeze_message: __('Saving Leave Encashments...'),
		}).then((r) => {
			const m = r.message;
			let msg = __('Created: {0}, Updated: {1}', [m.created.length, m.updated.length]);
			if (m.skipped.length) {
				msg += '<br><br>' + __('Skipped: {0}', [m.skipped.length]) + '<ul>' +
					m.skipped.map((s) => `<li>${frappe.utils.escape_html(s.employee)}: ${frappe.utils.escape_html(s.reason)}</li>`).join('') + '</ul>';
			}
			frappe.msgprint(msg);
			return fetch_employees(emps);
		});
	});

	page.add_inner_button(__('Get Employees'), () => fetch_employees());
	page.add_inner_button(__('Calculate'), () => {
		const emps = targets(false);
		show_loader(__('Calculating...'));
		frappe.call({ method: `${API}.calculate`, args: { employees: emps } }).then((r) => {
			const res = r.message || {};
			employees.forEach((e) => {
				if (res[e.employee]) Object.assign(e, res[e.employee], { calculated: 1, saved: 0 });
			});
			render();
		}).catch(render);
	});

	// list is always live from Leave Allocation, so new employees appear on load
	fetch_employees();
};

import frappe
from frappe import _
from frappe.utils import flt, getdate


from attendance_correction.attendance_correction.overrides.leave_encashment import (
	get_leave_allocation_summary,
)


# Total Leaves is a fixed entitlement shown for every employee; only the remaining
# encashment days / amount change. Never derive it from allocations.
TOTAL_LEAVES = 32


def _encashable_allocations(employee=None):
	filters = {"docstatus": 1}
	if employee:
		filters["employee"] = ["in", employee] if isinstance(employee, (list, tuple)) else employee
	encashable = frappe.get_all("Leave Type", filters={"allow_encashment": 1}, pluck="name")
	if not encashable:
		return []
	filters["leave_type"] = ["in", encashable]
	return frappe.get_all(
		"Leave Allocation", filters=filters, fields=["employee", "employee_name", "total_leaves_allocated"]
	)


def _employee_ids():
	return sorted({a.employee for a in _encashable_allocations()})


@frappe.whitelist()
def get_employees(employees=None):
	"""Every employee (or only the given ones) with a submitted Leave Allocation of an encashable
	Leave Type, with the days/amount already stored in their draft Leave Encashments (if any)."""
	frappe.has_permission("Leave Allocation", "read", throw=True)
	employees = frappe.parse_json(employees) if employees else None

	rows = {}
	for a in sorted(_encashable_allocations(employees), key=lambda a: a.employee):
		r = rows.setdefault(
			a.employee,
			{
				"employee": a.employee,
				"employee_name": a.employee_name,
				"department": "",
				"total_leaves": TOTAL_LEAVES,
				"days": 0,
				"total": 0,
				"saved": 0,
			},
		)

	if rows:
		for emp in frappe.get_all(
			"Employee", filters={"name": ["in", list(rows)]}, fields=["name", "department"]
		):
			rows[emp.name]["department"] = emp.department or ""

	for e in frappe.get_all(
		"Leave Encashment",
		filters={"docstatus": 0, "employee": ["in", list(rows)]} if rows else {"name": ""},
		fields=["employee", "encashment_days", "encashment_amount"],
	):
		r = rows[e.employee]
		r["days"] += flt(e.encashment_days)
		r["total"] += flt(e.encashment_amount)
		r["saved"] = 1

	return list(rows.values())


@frappe.whitelist()
def calculate(employees=None):
	"""Remaining encashment days and amount per employee, summed over encashable Leave Types."""
	frappe.has_permission("Leave Allocation", "read", throw=True)
	employees = frappe.parse_json(employees) if employees else _employee_ids()

	result = {}
	for emp in employees:
		rows = get_leave_allocation_summary(emp)
		result[emp] = {
			"days": sum(flt(r["encashment_days"]) for r in rows),
			"total": sum(flt(r["encashment_amount"]) for r in rows),
		}
	return result


@frappe.whitelist()
def save_encashments(employees=None):
	"""Store the calculation as Leave Encashment drafts: create one per employee + allocation,
	refresh the existing draft otherwise. Submitted encashments are left alone."""
	frappe.has_permission("Leave Encashment", "create", throw=True)
	employees = frappe.parse_json(employees) if employees else _employee_ids()

	created, updated, skipped = [], [], []
	for emp in employees:
		for row in get_leave_allocation_summary(emp):
			alloc = row["leave_allocation"]
			existing = frappe.get_all(
				"Leave Encashment",
				filters={"leave_allocation": alloc, "docstatus": ["<", 2]},
				fields=["name", "docstatus"],
			)
			if existing and existing[0].docstatus == 1:
				skipped.append({"employee": emp, "leave_allocation": alloc, "reason": "Already submitted"})
				continue

			date = min(max(getdate(), getdate(row["from_date"])), getdate(row["to_date"]))
			savepoint = "enc_" + alloc.replace("-", "_")
			frappe.db.savepoint(savepoint)
			try:
				if existing:
					doc = frappe.get_doc("Leave Encashment", existing[0].name)
					doc.encashment_date = date
					doc.save()
					updated.append(doc.name)
				else:
					doc = frappe.get_doc(
						{
							"doctype": "Leave Encashment",
							"employee": emp,
							"leave_type": row["leave_type"],
							"encashment_date": date,
							"pay_via_payment_entry": 1,
						}
					).insert()
					created.append(doc.name)
			except Exception as e:
				frappe.db.rollback(save_point=savepoint)
				skipped.append(
					{"employee": emp, "leave_allocation": alloc, "reason": frappe.utils.strip_html(str(e))}
				)

	return {"created": created, "updated": updated, "skipped": skipped}

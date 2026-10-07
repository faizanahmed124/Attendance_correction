import frappe
from frappe.utils import add_days, format_datetime, formatdate, getdate

from attendance_correction.attendance_correction.api.attendance_correction_audit import (
	ALLOWED_FIELDS,
	parse_correction_comment,
)


@frappe.whitelist()
def get_audit(from_date, to_date, user=None):
	"""Attendance corrections made by `user` (or anyone) between from_date and to_date.

	Dates filter on when the correction was made, not on the attendance date.
	"""
	if not from_date or not to_date:
		frappe.throw("From Date and To Date are required")

	from_dt = getdate(from_date)
	to_dt = getdate(to_date)
	if from_dt > to_dt:
		frappe.throw("From Date cannot be after To Date")

	conditions = ""
	values = {"from_dt": from_dt, "to_dt": add_days(to_dt, 1)}
	if user:
		conditions = "AND c.owner = %(user)s"
		values["user"] = user

	comments = frappe.db.sql(
		f"""
		SELECT c.name, c.reference_name AS attendance, c.owner, c.creation, c.content,
			a.employee, a.employee_name, a.department, a.attendance_date
		FROM `tabComment` c
		INNER JOIN `tabAttendance` a ON a.name = c.reference_name
		WHERE c.reference_doctype = 'Attendance'
			AND c.comment_type = 'Info'
			AND c.creation >= %(from_dt)s AND c.creation < %(to_dt)s
			{conditions}
		ORDER BY c.creation DESC
		""",
		values,
		as_dict=True,
	)

	names = {}
	rows = []
	seen = set()

	for c in comments:
		if c.owner not in names:
			names[c.owner] = frappe.db.get_value("User", c.owner, "full_name") or c.owner

		for ch in parse_correction_comment(c.content or ""):
			if ch["field"].lower() not in ALLOWED_FIELDS:
				continue

			# one row per distinct change (same user, record, field, values, minute)
			key = (
				c.attendance, c.owner, ch["field"].lower(), ch["from_value"], ch["to_value"],
				c.creation.strftime("%Y-%m-%d %H:%M"),
			)
			if key in seen:
				continue
			seen.add(key)

			rows.append({
				"changed_on": format_datetime(c.creation, "dd-MM-yyyy HH:mm"),
				"user": c.owner,
				"user_name": names[c.owner],
				"attendance": c.attendance,
				"employee": c.employee,
				"employee_name": c.employee_name,
				"department": c.department or "",
				"attendance_date": formatdate(c.attendance_date, "dd-MM-yyyy") if c.attendance_date else "",
				"field": ch["field"],
				"from_value": ch["from_value"],
				"to_value": ch["to_value"],
			})

	return rows

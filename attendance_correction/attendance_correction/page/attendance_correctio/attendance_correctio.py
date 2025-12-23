import frappe
import json
from frappe.model.document import Document


@frappe.whitelist()
def get_attendance_records(employee=None, shift=None, from_date=None, to_date=None):
    filters = {}

    if employee:
        filters["employee"] = employee
    if shift:
        filters["shift"] = shift
    if from_date and to_date:
        filters["attendance_date"] = ["between", [from_date, to_date]]

    return frappe.get_all(
        "Attendance",
        filters=filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "attendance_date",
            "status",
            "working_hours",
            "custom_overtime",  # 👈 OVERTIME column
            "in_time",
            "out_time",
            "docstatus"
        ]
    )


@frappe.whitelist()
def update_attendance(data):
    data = json.loads(data)
    updated = 0

    for row in data:
        if not row.get("name"):
            continue

        docname = row["name"]

        # Get employee from Attendance
        employee = frappe.db.get_value("Attendance", docname, "employee")

        # Check overtime permission
        allow_overtime = frappe.db.get_value(
            "Employee",
            employee,
            "custom_allow_overtime"
        )

        incoming_overtime = float(row.get("custom_overtime") or 0)


        # ❌ BLOCK overtime if not allowed
        if not allow_overtime and incoming_overtime > 0:
            frappe.throw(
                f"❌ Sorry, overtime isn’t allowed for employee: {employee}",
                frappe.PermissionError
            )

        # 1️⃣ Unlink Employee Checkins
        frappe.db.sql("""
            UPDATE `tabEmployee Checkin`
            SET attendance = NULL
            WHERE attendance = %s
        """, docname)

        # 2️⃣ Cancel Attendance
        frappe.db.set_value(
            "Attendance",
            docname,
            "docstatus",
            2,
            update_modified=False
        )

        # 3️⃣ Update & Re-submit Attendance
        frappe.db.set_value(
            "Attendance",
            docname,
            {
                "status": row.get("status"),
                "working_hours": row.get("working_hours"),
                "custom_overtime": incoming_overtime if allow_overtime else 0,
                "in_time": row.get("in_time"),
                "out_time": row.get("out_time"),
                "docstatus": 1
            },
            update_modified=False
        )

        updated += 1

    frappe.db.commit()
    return f"{updated} Attendance record(s) corrected successfully"


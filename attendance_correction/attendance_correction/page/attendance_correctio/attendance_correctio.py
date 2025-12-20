import frappe
import json
from frappe.model.document import Document


@frappe.whitelist()
def get_attendance_records(employee=None, shift=None, date=None):
    filters = {}

    if employee:
        filters["employee"] = employee
    if shift:
        filters["shift"] = shift
    if date:
        filters["attendance_date"] = date

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
            "custom_overtime", 
            "in_time",
            "out_time",
            "docstatus"
        ]
    )

@frappe.whitelist()
def update_attendance(data):
    import json
    data = json.loads(data)
    updated = 0

    for row in data:
        if not row.get("name"):
            continue

        docname = row["name"]

        # -----------------------------------
        # 1️⃣ Unlink Employee Checkins (SAFE)
        # -----------------------------------
        frappe.db.sql("""
            UPDATE `tabEmployee Checkin`
            SET attendance = NULL
            WHERE attendance = %s
        """, docname)

        # -----------------------------------
        # 2️⃣ Cancel Attendance (force)
        # -----------------------------------
        frappe.db.set_value(
            "Attendance",
            docname,
            "docstatus",
            2,
            update_modified=False
        )

        # -----------------------------------
        # 3️⃣ Update Attendance & re-submit
        # -----------------------------------
        frappe.db.set_value(
            "Attendance",
            docname,
            {
                "status": row.get("status"),
                "working_hours": row.get("working_hours"),
                "custom_overtime": row.get("custom_overtime"),  # 👈 SAVE OVERTIME
                "in_time": row.get("in_time"),
                "out_time": row.get("out_time"),
                "docstatus": 1
            },
            update_modified=False
        )

        updated += 1

    frappe.db.commit()
    return f"{updated} Attendance record(s) corrected successfully"


import frappe
import json
from frappe.model.document import Document
from frappe.utils import flt


@frappe.whitelist()
def get_attendance_records(employee=None, department=None, shift=None, from_date=None, to_date=None):
    filters = {}

    if employee:
        filters["employee"] = employee
    if department:
        filters["department"] = department
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

        # 🔹 Load full Attendance doc (for logging)
        attendance_doc = frappe.get_doc("Attendance", docname)

        # 🔹 Store OLD values (for comparison)
        old_status = attendance_doc.status
        old_working_hours = flt(attendance_doc.working_hours)
        old_overtime = flt(attendance_doc.custom_overtime or 0)
        old_in_time = attendance_doc.in_time
        old_out_time = attendance_doc.out_time

        # Get employee from Attendance
        employee = attendance_doc.employee

        # Check overtime permission
        allow_overtime = frappe.db.get_value(
            "Employee",
            employee,
            "custom_allow_overtime"
        )

        incoming_overtime = flt(row.get("custom_overtime") or 0)

        # 🔒 Decide final overtime
        if allow_overtime:
            final_overtime = incoming_overtime
        else:
            final_overtime = old_overtime

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

        # 3️⃣ Update Attendance
        frappe.db.set_value(
            "Attendance",
            docname,
            {
                "status": row.get("status"),
                "working_hours": row.get("working_hours"),
                "custom_overtime": final_overtime,
                "in_time": row.get("in_time"),
                "out_time": row.get("out_time"),
                "docstatus": 1
            },
            update_modified=False
        )

        # 🔴 🔴 🔴 NEW: CREATE LOG MESSAGE 🔴 🔴 🔴
        logs = []

        if old_status != row.get("status"):
            logs.append(
                f"Status changed from <b>{old_status}</b> → <b>{row.get('status')}</b>"
            )

        if old_working_hours != flt(row.get("working_hours")):
            logs.append(
                f"Working Hours changed from <b>{old_working_hours}</b> → <b>{row.get('working_hours')}</b>"
            )

        if old_overtime != flt(final_overtime):
            logs.append(
                f"Overtime changed from <b>{old_overtime}</b> → <b>{final_overtime}</b>"
            )

        if old_in_time != row.get("in_time"):
            logs.append(
                f"In Time changed from <b>{old_in_time or '-'} </b> → <b>{row.get('in_time') or '-'}</b>"
            )

        if old_out_time != row.get("out_time"):
            logs.append(
                f"Out Time changed from <b>{old_out_time or '-'} </b> → <b>{row.get('out_time') or '-'}</b>"
            )

        # 📝 Add timeline comment
        if logs:
            attendance_doc.add_comment(
                "Info",
                "<br>".join(logs)
            )

        updated += 1

    frappe.db.commit()
    return f"{updated} Attendance record(s) corrected successfully"



import frappe
import json
from frappe.model.document import Document
from frappe.utils import flt, formatdate, format_datetime
from datetime import datetime

# -----------------------------
# Helper Function
# -----------------------------
def convert_to_mysql_datetime(dt_str):
    """
    Convert 'DD-MM-YYYY HH:mm' or 'DD-MM-YYYY' to MySQL DATETIME 'YYYY-MM-DD HH:MM:SS'
    If input is None or empty, return None
    """
    if not dt_str:
        return None
    try:
        # Check if time is included
        if len(dt_str.strip()) > 10:
            dt_obj = datetime.strptime(dt_str, "%d-%m-%Y %H:%M")
        else:
            dt_obj = datetime.strptime(dt_str, "%d-%m-%Y")
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        frappe.log_error(f"Date conversion failed for '{dt_str}': {e}", "Attendance Date Conversion")
        return None

# -----------------------------
# Get Attendance Records
# -----------------------------
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

    attendance_records = frappe.get_all(
        "Attendance",
        filters=filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "attendance_date",
            "status",
            "custom_duty_hours",
            "custom_overtime",
            "in_time",
            "out_time",
            "docstatus"
        ],
        order_by="attendance_date ASC"
    )

    # 🔹 Convert to frontend-friendly format (DD-MM-YYYY)
    for row in attendance_records:
        if row.get("attendance_date"):
            row["attendance_date"] = formatdate(row["attendance_date"], "dd-MM-yyyy")
        if row.get("in_time"):
            row["in_time"] = format_datetime(row["in_time"], "dd-MM-yyyy HH:mm")
        if row.get("out_time"):
            row["out_time"] = format_datetime(row["out_time"], "dd-MM-yyyy HH:mm")

    return attendance_records

# -----------------------------
# Update Attendance Records
# -----------------------------
@frappe.whitelist()
def update_attendance(data):
    data = json.loads(data)
    updated = 0

    for row in data:
        if not row.get("name"):
            continue

        docname = row["name"]
        attendance_doc = frappe.get_doc("Attendance", docname)

        # OLD values
        old_status = attendance_doc.status
        old_duty_hours = flt(attendance_doc.custom_duty_hours or 0)
        old_overtime = flt(attendance_doc.custom_overtime or 0)
        old_in_time = attendance_doc.in_time
        old_out_time = attendance_doc.out_time

        employee = attendance_doc.employee
        allow_overtime = frappe.db.get_value("Employee", employee, "custom_allow_overtime")
        incoming_overtime = flt(row.get("custom_overtime") or 0)
        final_overtime = incoming_overtime if allow_overtime else old_overtime

        # Unlink Employee Checkins
        frappe.db.sql("""
            UPDATE `tabEmployee Checkin`
            SET attendance = NULL
            WHERE attendance = %s
        """, docname)

        # Cancel Attendance
        frappe.db.set_value("Attendance", docname, "docstatus", 2, update_modified=False)

        # Convert datetime to MySQL format
        in_time_mysql = convert_to_mysql_datetime(row.get("in_time"))
        out_time_mysql = convert_to_mysql_datetime(row.get("out_time"))

        # Update Attendance
        frappe.db.set_value(
            "Attendance",
            docname,
            {
                "status": row.get("status"),
                "custom_duty_hours": row.get("custom_duty_hours", 0),
                "custom_overtime": final_overtime,
                "in_time": in_time_mysql,
                "out_time": out_time_mysql,
                "docstatus": 1
            },
            update_modified=False
        )

        # Logs
        logs = []
        if old_status != row.get("status"):
            logs.append(f"Status changed from <b>{old_status}</b> → <b>{row.get('status')}</b>")
        if old_duty_hours != flt(row.get("custom_duty_hours", 0)):
            logs.append(f"Duty Hours changed from <b>{old_duty_hours}</b> → <b>{row.get('custom_duty_hours', 0)}</b>")
        if old_overtime != flt(final_overtime):
            logs.append(f"Overtime changed from <b>{old_overtime}</b> → <b>{final_overtime}</b>")
        if old_in_time != in_time_mysql:
            logs.append(f"In Time changed from <b>{old_in_time or '-'}</b> → <b>{in_time_mysql or '-'}</b>")
        if old_out_time != out_time_mysql:
            logs.append(f"Out Time changed from <b>{old_out_time or '-'}</b> → <b>{out_time_mysql or '-'}</b>")

        if logs:
            attendance_doc.add_comment("Info", "<br>".join(logs))

        updated += 1

    frappe.db.commit()
    return f"{updated} Attendance record(s) corrected successfully"








# SELECT
#     att.employee AS "Employee:Link/Employee:150",
#     att.employee_name AS "Employee Name:Link/Employee:150",
#     att.department AS "Department:Link/Department:150",
#     att.custom_employment_type AS "Employment Type::150",
#     att.attendance_date AS "Attendance Date:Date:120",
#     att.status AS "Status::150",
#     att.custom_duty_hours AS "Duty Hours:Float:120",
#     att.custom_overtime AS "Overtime Hours:Float:120",
    
#     att.in_time AS "In Time:Datetime:200",
#     att.out_time AS "Out Time:Datetime:200"

# FROM `tabAttendance` att

# WHERE att.docstatus != 2
# AND att.attendance_date BETWEEN %(from_date)s AND %(to_date)s
# AND att.department = %(department)s
# AND att.custom_employment_type = %(custom_employment_type)s


# ORDER BY att.attendance_date DESC